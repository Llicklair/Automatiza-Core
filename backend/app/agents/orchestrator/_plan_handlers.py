"""Node handlers: plan_node and its helpers (_plan_from_blueprint, _plan_from_llm)."""

import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agents.orchestrator.state import (
    VALID_DOMAINS,
    OrchestratorState,
    SubTask,
    TaskStatus,
)
from app.core.config import settings
from app.core.llm_factory import get_llm
from app.db.base import AsyncSessionLocal
from app.db.models.ai_employees import AIEmployee
from app.db.models.models import Workflow
from app.services.llm_cache import llm_cache

logger = logging.getLogger(__name__)


async def _employee_passes_health_check(emp: AIEmployee, db, *, builtin_fallback_domain: str | None = None) -> bool:
    """Health-check pre-dispatch para AIEmployees custom.

    Un empleado custom se considera SANO (apto para interceptar un dominio
    builtin) sólo si:
      1. status no es 'blocked' (idle/working/paused se aceptan; blocked NO).
      2. Tiene system_prompt no vacío (sin prompt el agente entra en bucle).
      3. Tiene al menos una entrada en AgentSkill (sin skills no puede operar).

    Si falla cualquier criterio se loguea un WARNING con el motivo y la
    función devuelve False — el caller debe hacer fallback al builtin.

    Devuelve True si el empleado es apto para ser dispatched.
    """
    from sqlalchemy import func

    from app.db.models.ai_employees import AgentSkill

    reasons: list[str] = []

    if (emp.status or "").lower() == "blocked":
        reasons.append(f"status={emp.status!r}")

    if not (emp.system_prompt or "").strip():
        reasons.append("system_prompt vacío")

    try:
        skills_count_row = await db.execute(select(func.count(AgentSkill.id)).where(AgentSkill.employee_id == emp.id))
        skills_count = int(skills_count_row.scalar() or 0)
    except Exception as e:
        # Si la query falla preferimos NO bloquear al empleado por seguridad de
        # disponibilidad (mejor intentar el custom que dejar al tenant sin nada).
        logger.debug("[HEALTH] No se pudo contar skills de '%s' (%s): %s", emp.name, emp.id, e)
        skills_count = -1  # señal: no se pudo verificar

    if skills_count == 0:
        reasons.append("sin AgentSkill registradas")

    if reasons:
        logger.warning(
            "AIEmployee '%s' (%s) custom omitido por health-check (%s), " "usando builtin '%s'",
            emp.name,
            emp.id,
            "; ".join(reasons),
            builtin_fallback_domain or emp.domain,
        )
        return False
    return True


async def _load_tenant_custom_employees(tenant_id: str) -> list[AIEmployee]:
    """Devuelve los AIEmployees custom (no builtin) y activos del tenant.
    Lista ordenada por nombre para que el cache key sea estable.

    Fase health-check: además del filtro SQL básico (no builtin + status
    idle/working) aplicamos _employee_passes_health_check para descartar
    empleados con prompt vacío o sin skills. Esto evita que un AIEmployee
    custom mal configurado intercepte el dispatch de un builtin y produzca
    timeouts (ver lessons 2026-05-18).
    """
    if not tenant_id:
        return []
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AIEmployee)
                .where(
                    AIEmployee.tenant_id == UUID(tenant_id),
                    AIEmployee.is_builtin.is_(False),
                    AIEmployee.status.in_(("idle", "working")),
                )
                .order_by(AIEmployee.name)
            )
            candidates = list(result.scalars().all())
            healthy: list[AIEmployee] = []
            for emp in candidates:
                if await _employee_passes_health_check(emp, db):
                    healthy.append(emp)
            return healthy
    except Exception as e:
        logger.debug("[PLAN] No se pudieron cargar custom employees: %s", e)
        return []


def _custom_employees_block(employees: list[AIEmployee]) -> str:
    """Bloque de texto para inyectar al prompt del planner.
    Lista los AIEmployees custom disponibles con un resumen del expertise
    (primeras frases del system_prompt) para que el LLM pueda elegirlos
    cuando el rol encaje con la tarea, mencionados explícitamente o no.
    """
    if not employees:
        return ""

    def _expertise_snippet(emp: AIEmployee) -> str:
        """Primer fragmento útil del system_prompt — el LLM lo usa para juzgar
        si el custom es apropiado para una sub-tarea."""
        text = (emp.system_prompt or "").strip()
        # Tomamos las primeras ~200 caracteres, cortando en frase si se puede.
        snippet = text[:240].replace("\n", " ").strip()
        if len(text) > 240:
            cut = max(snippet.rfind(". "), snippet.rfind("; "), 0)
            snippet = snippet[: cut + 1] if cut > 80 else snippet + "..."
        return snippet

    lines = [
        f'  - "{emp.name}" — {emp.role} (employee_id: "{emp.id}")\n' f"      Expertise: {_expertise_snippet(emp)}"
        for emp in employees
    ]
    return (
        "\nAGENTES CUSTOM DEL TENANT (además de los builtin):\n"
        + "\n".join(lines)
        + (
            "\nUSO: si el rol/expertise de un custom encaja con una sub-tarea, "
            'asígnasela usando agent="custom" y rellenando employee_id con su id, '
            "AUNQUE el usuario no lo mencione por nombre. Ejemplo: una tarea de "
            'visión técnica/coordinación ejecutiva puede ir a un "CTO" custom '
            "aunque el prompt solo describa el resultado deseado. "
            'Formato: {"agent": "custom", "employee_id": "<uuid>", "instruction": "..."}.\n'
            "PRECEDENCIA: prefiere builtin para tareas directas y bien tipadas "
            "(crear factura, generar nómina, conciliar banca). Reserva los custom "
            "para tareas de coordinación, supervisión, análisis transversal o "
            "expertise específico que el builtin no cubre.\n"
        )
    )


def _custom_employees_hash(employees: list[AIEmployee]) -> str:
    """Hash estable del set de custom employees, para invalidar caché si cambia."""
    if not employees:
        return "no-custom"
    payload = "|".join(f"{emp.id}:{emp.name}:{emp.role}" for emp in employees)
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


async def _plan_from_blueprint(state: OrchestratorState, wf) -> "list[SubTask] | None":
    """
    Convierte ui_nodes de un Workflow en SubTasks.
    Devuelve None si el blueprint está vacío.
    Delega a NodeEngine si hay nodos avanzados (y devuelve plan marcado como done).
    """
    from app.services.ai.node_graph_helpers import has_advanced_nodes

    if not wf or not wf.ui_nodes:
        return None

    if has_advanced_nodes(wf.ui_nodes):
        logger.info("[PLAN] Workflow '%s' tiene nodos avanzados → delegando a NodeEngine", wf.name)
        execution_id = (state.get("additional_metadata") or {}).get("execution_id")
        if execution_id:
            try:
                from app.services.workflow.task_dispatch import dispatch_node_engine

                await dispatch_node_engine(execution_id)
            except Exception as ce:
                logger.error("[PLAN] Error lanzando NodeEngine: %s", ce)
        return [
            {
                "id": "node_engine",
                "agent": "node_engine",
                "action": "delegated",
                "params": {},
                "depends_on": [],
                "status": "done",
            }
        ]

    logger.info("[PLAN] Siguiendo blueprint del workflow '%s'", wf.name)
    action_nodes = [n for n in wf.ui_nodes if n.get("type") in ("action", "skill")]
    edges = wf.ui_edges or []
    plan: list[SubTask] = []
    for node in action_nodes:
        node_id = node["id"]
        data = node.get("data", {})
        deps = [e["source"] for e in edges if e["target"] == node_id]
        final_deps = [d for d in deps if any(an["id"] == d for an in action_nodes)]
        explicit = data.get("instruction") or data.get("description") or ""
        raw = explicit if explicit.strip() else data.get("label", "")
        node_intent = raw if (raw and len(raw.split()) > 3) else state["user_intent"]
        params: dict = {"intent": node_intent, "original_node_id": node_id}
        # Si el nodo trae employee_id (asignado en el modal a un AIEmployee
        # custom), propágalo a params para que _invoke_dynamic_employee lo use.
        if data.get("employee_id"):
            params["employee_id"] = data["employee_id"]
        plan.append(
            {
                "id": node_id,
                # Default a "chat" (dispatcher real) y NO "coordinator": coordinator
                # no está en DISPATCHER_MAP → caía al fallback que devuelve
                # success=True sin ejecutar nada (éxito silencioso). chat al menos
                # procesa el intent del nodo.
                "agent": data.get("domain", "chat"),
                "action": "execute_node",
                "params": params,
                "depends_on": final_deps,
                "status": "pending",
            }
        )
    return plan if plan else None


async def _plan_from_llm(state: OrchestratorState) -> "list[SubTask]":
    """Descompone la tarea via LLM con caché y fallback de proveedor."""

    class PlanStep(BaseModel):
        agent: str = Field(
            description="Dominios válidos: hr, crm, excel, email, billing, documents, banking, rag, workflow, compliance, recruitment, marketing, inventory, chat, custom"
        )
        action: str = Field(description="Acción corta, ej: extract_data, create_report, send_email")
        instruction: str = Field(description="Instrucción muy detallada en español para el agente actual.")
        needs_output_from: list[int] = Field(
            default_factory=list, description="Índices (1-based) de pasos anteriores requeridos."
        )
        employee_id: str | None = Field(
            default=None,
            description=(
                "ID (UUID) del AIEmployee custom. SOLO cuando agent='custom'. "
                "Debe ser uno de los IDs listados en AGENTES CUSTOM DISPONIBLES."
            ),
        )

    class MultiAgentPlan(BaseModel):
        steps: list[PlanStep] = Field(description="Lista de pasos para resolver la tarea.")

    _tenant_id = state.get("tenant_id", "")

    # Lista de custom employees del tenant para inyectar al prompt del planner
    # y para construir cache key estable que se invalide si el set cambia.
    custom_employees = await _load_tenant_custom_employees(_tenant_id)
    custom_block = _custom_employees_block(custom_employees)
    custom_hash = _custom_employees_hash(custom_employees)
    _cache_key = f"plan:{custom_hash}:{state['user_intent']}"

    # Intentar desde caché
    _cached = await llm_cache.get(_tenant_id, _cache_key)
    if _cached:
        try:
            _data = json.loads(_cached)
            plan: list[SubTask] = []
            valid = True
            for idx, step in enumerate(_data.get("steps", [])):
                agent = step.get("agent", "")
                if agent not in VALID_DOMAINS:
                    logger.warning("[PLAN] Caché contiene agente inválido '%s', descartando", agent)
                    valid = False
                    break
                raw_deps = step.get("needs_output_from", []) or []
                params: dict = {"intent": step.get("instruction", "")}
                if agent == "custom" and step.get("employee_id"):
                    params["employee_id"] = step["employee_id"]
                plan.append(
                    {
                        "id": f"step_{idx + 1}",
                        "agent": agent,
                        "action": step.get("action", "process"),
                        "params": params,
                        "depends_on": [f"step_{d}" for d in raw_deps if isinstance(d, int) and 1 <= d <= idx],
                        "status": "pending",
                    }
                )
            if plan and valid:
                return plan
            if not valid:
                try:
                    await llm_cache.invalidate(_tenant_id, _cache_key)
                except Exception:
                    logger.debug("No se pudo invalidar la caché del plan; continúo", exc_info=True)
        except Exception:
            logger.debug("Caché de plan corrupto, continuando con LLM", exc_info=True)

    # Invocar LLM con retry y fallback de proveedor
    llm = get_llm(temperature=0)
    structured_llm = llm.with_structured_output(MultiAgentPlan, method="json_mode")
    prompt = (
        "Eres el asistente de gestión empresarial para PYMEs españolas.\n"
        "Conoces el PGC 2007, la normativa AEAT, tipos de IVA (21%/10%/4%/0%), "
        "Seguridad Social (CC 4,70%, desempleo 1,55%, FP 0,10%, MEI según el año "
        "—0,13% en 2025, 0,15% en 2026—) y el ET.\n"
        f"La empresa opera en euros bajo ley española. Hoy es {datetime.now(UTC).strftime('%d/%m/%Y')}.\n\n"
        "Descompón la petición en pasos MÍNIMOS usando SOLO los agentes necesarios. Ejecución puntual — NO crees reglas recurrentes.\n\n"
        f"Petición: {state['user_intent']}\n\n"
        "AGENTES BUILTIN: billing, hr, crm, banking, email, compliance, documents, rag, excel\n"
        + custom_block
        + "REGLAS: mínimo de pasos; excel para hojas/informes; billing guarda facturas internamente; "
        "email como último paso si se pide notificación; NIF en facturas; mes/año en nóminas.\n"
        "PARALELISMO: needs_output_from con índices (1-based) de pasos requeridos; vacío = paralelo.\n\n"
        'JSON: {"steps": [{"agent": "...", "action": "...", "instruction": "...", "needs_output_from": [], "employee_id": null}]}'
    )

    plan_result = None
    last_exc = None
    for attempt in range(3):
        try:
            plan_result = await asyncio.wait_for(structured_llm.ainvoke(prompt), timeout=60)
            break
        except Exception as exc:
            last_exc = exc
            err_str = str(exc)
            if (
                "ResourceExhausted" in type(exc).__name__
                or "429" in err_str
                or "quota" in err_str.lower()
                or "500" in err_str
            ):
                if attempt == 0 and settings.GROQ_API_KEY:
                    logger.warning("[PLAN] Proveedor principal caído, intentando Groq...")
                    try:
                        structured_llm = get_llm(temperature=0, provider="groq").with_structured_output(
                            MultiAgentPlan, method="json_mode"
                        )
                        continue
                    except Exception:
                        logger.debug("Fallback a Groq falló", exc_info=True)
                fallback_llm = (
                    get_llm(temperature=0, provider="openai") if settings.OPENAI_API_KEY else get_llm(temperature=0)
                )
                structured_llm = fallback_llm.with_structured_output(MultiAgentPlan, method="json_mode")
                continue
            elif attempt < 2:
                await asyncio.sleep(5 * (attempt + 1))
            else:
                raise

    if plan_result is None:
        raise last_exc or ValueError("No se pudo obtener respuesta del LLM")
    if not hasattr(plan_result, "steps") or plan_result.steps is None:
        raise ValueError("El LLM no devolvió los pasos en el formato esperado")

    # Cachear plan (TTL 1h)
    try:
        await llm_cache.set(
            _tenant_id,
            _cache_key,
            json.dumps(
                {
                    "steps": [
                        {
                            "agent": s.agent,
                            "action": s.action,
                            "instruction": s.instruction,
                            "needs_output_from": getattr(s, "needs_output_from", []) or [],
                            "employee_id": getattr(s, "employee_id", None),
                        }
                        for s in plan_result.steps
                    ]
                }
            ),
            ttl_override=3600,
        )
    except Exception:
        logger.debug("Error guardando plan en caché", exc_info=True)

    # Validate that any employee_id returned by the LLM matches a real custom
    # employee of this tenant — defense against LLM hallucinated UUIDs.
    valid_employee_ids = {str(e.id) for e in custom_employees}

    plan = []
    for idx, step in enumerate(plan_result.steps):
        agent = step.agent if step.agent in VALID_DOMAINS else "unknown"
        raw_deps = getattr(step, "needs_output_from", None) or []
        params = {"intent": step.instruction}
        emp_id = getattr(step, "employee_id", None)
        if agent == "custom" and emp_id and emp_id in valid_employee_ids:
            params["employee_id"] = emp_id
        elif agent == "custom" and emp_id and emp_id not in valid_employee_ids:
            logger.warning("[PLAN] LLM devolvió employee_id desconocido '%s', ignorando", emp_id)
        plan.append(
            {
                "id": f"step_{idx + 1}",
                "agent": agent,
                "action": step.action,
                "params": params,
                "depends_on": [f"step_{d}" for d in raw_deps if isinstance(d, int) and 1 <= d <= idx],
                "status": "pending",
            }
        )
    return plan


async def plan_node(state: OrchestratorState) -> dict:
    """
    Descompone la tarea en subtareas usando:
    1. Blueprint del Workflow si existe en los metadatos.
    2. LLM multiagente si el dominio es 'coordinator'.
    3. Plan de un solo paso para dominios simples.
    """
    # 1. Blueprint de Workflow
    workflow_id = (state.get("additional_metadata") or {}).get("workflow_id")
    if workflow_id:
        try:
            async with AsyncSessionLocal() as db:
                wf_res = await db.execute(select(Workflow).where(Workflow.id == UUID(workflow_id)))
                wf = wf_res.scalar_one_or_none()
                plan = await _plan_from_blueprint(state, wf)
                if plan is not None:
                    status = TaskStatus.DONE if plan[0].get("status") == "done" else TaskStatus.EXECUTING
                    return {"plan": plan, "status": status}
        except Exception as e:
            logger.warning("[PLAN] Error cargando blueprint: %s. Cayendo a planificación estándar.", e)

    # 2. LLM coordinator
    domain = state["classified_domain"]
    if domain == "coordinator":
        try:
            plan = await _plan_from_llm(state)
        except Exception as e:
            logger.exception("Error planificando tarea")
            return {
                **state,
                "plan": [],
                "status": TaskStatus.FAILED,
                "error_message": f"Error planificando tarea: {type(e).__name__}: {e}",
                "iteration_count": state["iteration_count"] + 1,
            }
    # 3. Plan de un solo agente — defensa: si el dominio no es válido caemos a 'chat'
    else:
        single_agent = domain if domain in VALID_DOMAINS else "chat"

        # Short-circuit: si el usuario dirigió la task a un AIEmployee BUILTIN
        # específico (via /instruct con addressed_employee_id), respetar su
        # domain y planear 1 paso directo. SIN esto, el escalado al planner
        # LLM (cuando hay 2+ customs del mismo domain) descomponía tasks
        # atómicas en multi-agent — bug 5A del coordinator (visible en HR:
        # "Aprueba todas las nóminas" terminaba con hr + custom + custom).
        metadata = state.get("additional_metadata") or {}
        addressed_id = metadata.get("addressed_employee_id")
        if addressed_id:
            try:
                async with AsyncSessionLocal() as db:
                    _r = await db.execute(select(AIEmployee).where(AIEmployee.id == UUID(addressed_id)))
                    _emp = _r.scalar_one_or_none()
                if _emp and _emp.is_builtin and _emp.domain in VALID_DOMAINS:
                    plan = [
                        {
                            "id": "step_1",
                            "agent": str(_emp.domain),
                            "action": "process",
                            "params": {"intent": state["user_intent"]},
                            "depends_on": [],
                            "status": "pending",
                        }
                    ]
                    return {
                        **state,
                        "plan": plan,
                        "status": TaskStatus.VALIDATING,
                        "iteration_count": state["iteration_count"] + 1,
                    }
            except Exception as _e:
                logger.debug(
                    "[PLAN] lookup de addressed builtin falló: %s. Sigo el flujo estándar.",
                    _e,
                )

        # Si el tenant tiene AIEmployees custom para este dominio, evitar que el
        # built-in se trague la tarea sin más. 1 match → atajo directo a custom;
        # 2+ → escalar al planner LLM para que elija con criterio (rol/expertise).
        custom_match: AIEmployee | None = None
        if domain in VALID_DOMAINS:
            try:
                tenant_id_str = state.get("tenant_id", "") or ""
                all_customs = await _load_tenant_custom_employees(tenant_id_str)
                matching = [e for e in all_customs if e.domain == domain]
                if len(matching) == 1:
                    custom_match = matching[0]
                elif len(matching) >= 2:
                    try:
                        plan = await _plan_from_llm(state)
                        return {
                            **state,
                            "plan": plan,
                            "status": TaskStatus.VALIDATING,
                            "iteration_count": state["iteration_count"] + 1,
                        }
                    except Exception as e:
                        logger.warning(
                            "[PLAN] escalación a planner falló (%s), caigo a builtin '%s'",
                            e,
                            single_agent,
                        )
            except Exception as e:
                logger.debug("[PLAN] custom lookup falló: %s", e)

        if custom_match is not None:
            plan = [
                {
                    "id": "step_1",
                    "agent": "custom",
                    "action": "process",
                    "params": {
                        "intent": state["user_intent"],
                        "employee_id": str(custom_match.id),
                    },
                    "depends_on": [],
                    "status": "pending",
                }
            ]
        else:
            plan = [
                {
                    "id": "step_1",
                    "agent": single_agent,
                    "action": "process",
                    "params": {"intent": state["user_intent"]},
                    "depends_on": [],
                    "status": "pending",
                }
            ]

    return {
        **state,
        "plan": plan,
        "status": TaskStatus.VALIDATING,
        "iteration_count": state["iteration_count"] + 1,
    }
