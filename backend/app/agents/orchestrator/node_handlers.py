"""
Node handler functions for the LangGraph orchestrator.

Each async function corresponds to a node in the orchestrator graph:
  init_tenant_node  — Load tenant LLM config
  load_knowledge_node — Load tenant knowledge facts
  plan_node         — Decompose task into subtasks (blueprint or LLM)
  validate_node     — Pre-execution validation
  dispatch_node     — Invoke specialized agents (parallel, retry, dynamic employees)
  summarize_node    — Generate conversational summary of results
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from app.agents.orchestrator.dispatchers import DISPATCHER_MAP
from app.agents.orchestrator.state import (
    MAX_ITERATIONS,
    VALID_DOMAINS,
    AgentResult,
    OrchestratorState,
    SubTask,
    TaskStatus,
)

logger = logging.getLogger(__name__)


# ─── Nodo: inicializar LLM del tenant (entry point) ─────────────────────────


async def init_tenant_node(state: OrchestratorState) -> dict:
    """Carga el LLM del tenant en el ContextVar ANTES de cualquier nodo que use LLM.
    Valida que el proveedor esté habilitado y tenga credenciales."""
    from uuid import UUID

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal

    tenant_id = state.get("tenant_id")
    if not tenant_id:
        return {
            "status": TaskStatus.FAILED,
            "error_message": "Falta tenant_id — no se puede ejecutar sin contexto de empresa",
        }

    try:
        async with AsyncSessionLocal() as db:
            from app.db.models.models import TenantLlmConfig
            from app.services.encryption import decrypt_credentials

            cfg_result = await db.execute(
                select(TenantLlmConfig).where(TenantLlmConfig.tenant_id == UUID(tenant_id))
            )
            cfg = cfg_result.scalar_one_or_none()
            if cfg and cfg.encrypted_keys:
                keys = decrypt_credentials(cfg.encrypted_keys)
                provider = cfg.active_llm_provider
                pdata = keys.get(provider, {})
                if not pdata.get("enabled", True):
                    return {
                        "status": TaskStatus.FAILED,
                        "error_message": (
                            f"El proveedor de IA '{provider}' está desactivado. "
                            "Actívalo en Configuración → API Keys."
                        ),
                    }
                from app.core.llm_factory import get_llm_for_tenant, set_tenant_llm_context

                _tenant_llm = await get_llm_for_tenant(tenant_id, db, temperature=0)
                set_tenant_llm_context(_tenant_llm)
                logger.info("[INIT] LLM del tenant cargado: provider=%s", provider)
            else:
                logger.info("[INIT] Sin config LLM para tenant %s, usando global", tenant_id)
    except ValueError:
        raise
    except Exception as e:
        logger.warning("No se pudo precargar LLM del tenant: %s", e)

    return {}


# ─── Nodo: cargar conocimiento del tenant ────────────────────────────────────


async def load_knowledge_node(state: OrchestratorState) -> dict:
    """Carga hechos y preferencias del TenantKnowledge para inyectar en el contexto."""
    from uuid import UUID

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantKnowledge

    tenant_id = state.get("tenant_id")
    if not tenant_id:
        return {"tenant_knowledge": []}

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TenantKnowledge).where(TenantKnowledge.tenant_id == UUID(tenant_id))
            )
            facts = result.scalars().all()

            knowledge_list = [
                {"key": f.key, "value": f.value, "category": f.category} for f in facts
            ]
            return {
                "tenant_knowledge": knowledge_list,
                "additional_metadata": {
                    **(state.get("additional_metadata") or {}),
                    "started_at": datetime.now(UTC).isoformat(),
                },
            }
    except Exception as e:
        logger.warning(f"Error cargando conocimiento: {e}")
        return {
            "tenant_knowledge": [],
            "additional_metadata": {
                **(state.get("additional_metadata") or {}),
                "started_at": datetime.now(UTC).isoformat(),
            },
        }


# ─── Nodo: planificación ─────────────────────────────────────────────────────


async def plan_node(state: OrchestratorState) -> dict:
    """
    Descompone la tarea en subtareas.
    Si hay un workflow_id en los metadatos, carga el blueprint (nodos y aristas) de la base de datos.
    Sino, usa el LLM para dividir la tarea compleja si el dominio es 'coordinator'.
    """
    from uuid import UUID

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Workflow

    # ── Atajo 1: Seguir un Blueprint de Workflow si existe ───────────────────
    workflow_id = (state.get("additional_metadata") or {}).get("workflow_id")
    if workflow_id:
        try:
            async with AsyncSessionLocal() as db:
                wf_res = await db.execute(select(Workflow).where(Workflow.id == UUID(workflow_id)))
                wf = wf_res.scalar_one_or_none()

                if wf and wf.ui_nodes:
                    # ── Si tiene nodos avanzados, delegar al NodeEngine ──
                    from app.services.node_engine import has_advanced_nodes

                    if has_advanced_nodes(wf.ui_nodes):
                        logger.info(
                            f"[PLAN] Workflow '{wf.name}' tiene nodos avanzados → delegando a NodeEngine"
                        )
                        execution_id = (state.get("additional_metadata") or {}).get("execution_id")
                        if execution_id:
                            try:
                                from app.services.task_dispatch import dispatch_node_engine

                                await dispatch_node_engine(execution_id)
                            except Exception as ce:
                                logger.error(f"[PLAN] Error lanzando NodeEngine: {ce}")
                        return {
                            "plan": [
                                {
                                    "id": "node_engine",
                                    "agent": "node_engine",
                                    "action": "delegated",
                                    "params": {},
                                    "depends_on": [],
                                    "status": "done",
                                }
                            ],
                            "status": TaskStatus.DONE,
                        }

                    logger.info(f"[PLAN] Siguiendo blueprint del workflow '{wf.name}'")
                    plan: list[SubTask] = []

                    # Filtrar solo nodos de tipo action/skill
                    action_nodes = [n for n in wf.ui_nodes if n.get("type") in ("action", "skill")]
                    edges = wf.ui_edges or []

                    for node in action_nodes:
                        node_id = node["id"]
                        data = node.get("data", {})

                        # Determinar dependencias basándonos en las aristas
                        deps = [e["source"] for e in edges if e["target"] == node_id]

                        # Solo dependemos de nodos que también estén en el plan (purgar triggers)
                        final_deps = [d for d in deps if any(an["id"] == d for an in action_nodes)]

                        # Prioridad: instruction explícita > description > label largo > user_intent
                        explicit = data.get("instruction") or data.get("description") or ""
                        fallback = data.get("label", "")
                        raw = explicit if explicit.strip() else fallback
                        node_intent = (
                            raw if (raw and len(raw.split()) > 3) else state["user_intent"]
                        )

                        plan.append(
                            {
                                "id": node_id,
                                "agent": data.get("domain", "coordinator"),
                                "action": "execute_node",
                                "params": {"intent": node_intent, "original_node_id": node_id},
                                "depends_on": final_deps,
                                "status": "pending",
                            }
                        )

                    if plan:
                        return {"plan": plan, "status": TaskStatus.EXECUTING}
        except Exception as e:
            logger.warning(
                f"[PLAN] Error cargando blueprint: {e}. Cayendo a planificación estándar."
            )

    domain = state["classified_domain"]

    if domain == "coordinator":
        try:
            from pydantic import BaseModel, Field

            class PlanStep(BaseModel):
                agent: str = Field(
                    description="Dominios válidos: hr, crm, excel, email, billing, documents, banking, rag, team (para crear/gestionar empleados IA), custom (para agentes IA personalizados del equipo)"
                )
                action: str = Field(
                    description="Acción corta, ej: extract_data, create_report, send_email"
                )
                instruction: str = Field(
                    description="Instrucción muy detallada en español para el agente actual que ejecutará el paso."
                )
                needs_output_from: list[int] = Field(
                    default_factory=list,
                    description="Índices (1-based) de pasos anteriores cuyo resultado necesita este paso. Vacío = independiente.",
                )

            class MultiAgentPlan(BaseModel):
                steps: list[PlanStep] = Field(
                    description="Lista de pasos para resolver la tarea. Pasos sin dependencias se ejecutan en paralelo."
                )

            import json as _json

            from app.core.config import settings
            from app.core.llm_factory import get_llm
            from app.services.llm_cache import llm_cache

            # Consultar caché de planificación
            _tenant_id = state.get("tenant_id", "")
            _plan_cache_key = f"plan:{state['user_intent']}"
            _cached_plan = await llm_cache.get(_tenant_id, _plan_cache_key)
            if _cached_plan:
                try:
                    _cached_data = _json.loads(_cached_plan)
                    plan: list[SubTask] = []
                    _cache_valid = True
                    for idx, step in enumerate(_cached_data.get("steps", [])):
                        agent = step.get("agent", "")
                        if agent not in VALID_DOMAINS:
                            logger.warning(
                                "[PLAN] Caché contiene agente inválido '%s', descartando entrada",
                                agent,
                            )
                            _cache_valid = False
                            break
                        raw_deps = step.get("needs_output_from", []) or []
                        deps = [
                            f"step_{d}" for d in raw_deps if isinstance(d, int) and 1 <= d <= idx
                        ]
                        plan.append(
                            {
                                "id": f"step_{idx + 1}",
                                "agent": agent,
                                "action": step.get("action", "process"),
                                "params": {"intent": step.get("instruction", "")},
                                "depends_on": deps,
                                "status": "pending",
                            }
                        )
                    if plan and _cache_valid:
                        return {"plan": plan, "status": TaskStatus.EXECUTING}
                    if not _cache_valid:
                        # Invalidar caché corrupto para que el próximo intento use el LLM
                        try:
                            await llm_cache.invalidate(_tenant_id, _plan_cache_key)
                        except Exception:
                            pass
                except Exception:
                    logger.debug("Caché de plan corrupto, continuando con LLM", exc_info=True)

            llm = get_llm(temperature=0)
            structured_llm = llm.with_structured_output(MultiAgentPlan, method="json_mode")

            prompt = (
                "Eres el asistente de gestión empresarial para PYMEs españolas.\n"
                "Conoces el Plan General Contable español (PGC 2007), la normativa de la AEAT, "
                "los tipos de IVA vigentes (general 21%, reducido 10%, superreducido 4%, exento 0%), "
                "el sistema de Seguridad Social español (contingencias comunes 4,70%, desempleo 1,55%, FP 0,10%, MEI 0,12%) "
                "y la legislación laboral del Estatuto de los Trabajadores.\n"
                "La empresa opera en euros (€) bajo ley española. Hoy es "
                + datetime.now().strftime("%d/%m/%Y")
                + ".\n\n"
                "Tu tarea: descompón la siguiente petición en pasos MÍNIMOS y ORDENADOS, usando SOLO los agentes necesarios.\n"
                "Esta es una ejecución puntual — NO crees reglas recurrentes.\n\n"
                f"Petición del usuario: {state['user_intent']}\n\n"
                "AGENTES DISPONIBLES:\n"
                "- billing: crear facturas, presupuestos o consultar facturación. Incluye generación de PDF automática.\n"
                "- hr: gestionar empleados, generar nóminas con cálculo de SS e IRPF, consultar contratos.\n"
                "- crm: gestionar clientes, oportunidades de venta, pipeline comercial.\n"
                "- banking: consultar saldos, movimientos bancarios o hacer conciliación.\n"
                "- email: revisar bandeja de entrada, redactar o enviar correos.\n"
                "- compliance: consultas fiscales (IVA, IRPF, IS), vencimientos tributarios, alertas BOE.\n"
                "- documents: archivar, clasificar o analizar documentos subidos (contratos, albaranes, etc.).\n"
                "- rag: buscar información en documentos internos de la empresa.\n"
                "- excel: generar archivo Excel (.xlsx) con datos de la empresa (facturas, empleados, clientes, nóminas, inventario, banco).\n"
                "- custom: agentes IA personalizados del equipo (CTO, marketing, diseño, etc.). Úsalo cuando la tarea corresponda a un rol no estándar del equipo.\n\n"
                "REGLAS:\n"
                "1. Usa el MÍNIMO de pasos posible. Evita pasos redundantes.\n"
                "2. Usa 'excel' cuando el usuario pida generar un Excel, informe tabular, listado en hoja de cálculo, exportar datos o cruzar ficheros CSV/Excel.\n"
                "3. NO uses 'documents' para guardar facturas (billing lo hace internamente).\n"
                "4. Si el usuario pide notificación por email, añade 'email' como último paso.\n"
                "5. Para crear facturas incluye SIEMPRE el NIF del cliente si lo menciona.\n"
                "6. Para nóminas especifica mes y año si se mencionan.\n"
                "7. PARALELISMO: indica en 'needs_output_from' los índices (1-based) de pasos cuyo resultado NECESITA este paso. "
                "Pasos independientes deben tener needs_output_from vacío ([]) para ejecutarse en paralelo. "
                "Ejemplo: si paso 1 (hr) y paso 2 (billing) son independientes, ambos llevan []. Si paso 3 (email) necesita los resultados de ambos, lleva [1,2].\n\n"
                "RESPONDE ÚNICAMENTE con JSON válido con EXACTAMENTE esta estructura:\n"
                '{"steps": [{"agent": "nombre_agente", "action": "accion_corta", "instruction": "instruccion detallada", "needs_output_from": []}]}'
            )

            plan_result = None
            last_exc = None
            for _attempt in range(3):
                try:
                    plan_result = await asyncio.wait_for(
                        structured_llm.ainvoke(prompt),
                        timeout=60,
                    )
                    break
                except Exception as _e:
                    last_exc = _e
                    err_str = str(_e)
                    # Si es error de cuota o servidor → fallback a Groq, luego OpenAI
                    if (
                        "ResourceExhausted" in type(_e).__name__
                        or "429" in err_str
                        or "quota" in err_str.lower()
                        or "500" in err_str
                    ):
                        if _attempt == 0 and settings.GROQ_API_KEY:
                            logger.warning(
                                f"[PLAN] Gemini caído (HTTP {err_str[:50]}), intentando Groq..."
                            )
                            try:
                                _fallback_llm = get_llm(temperature=0, provider="groq")
                                structured_llm = _fallback_llm.with_structured_output(
                                    MultiAgentPlan, method="json_mode"
                                )
                                continue
                            except Exception:
                                logger.debug("Fallback a Groq falló", exc_info=True)
                        logger.warning("[PLAN] Fallback final al proveedor secundario.")
                        _fallback_llm = (
                            get_llm(temperature=0, provider="openai")
                            if settings.OPENAI_API_KEY
                            else get_llm(temperature=0)
                        )
                        structured_llm = _fallback_llm.with_structured_output(
                            MultiAgentPlan, method="json_mode"
                        )
                        continue
                    # Si es error de red → esperar y reintentar
                    elif _attempt < 2:
                        await asyncio.sleep(5 * (_attempt + 1))
                    else:
                        raise

            if plan_result is None:
                raise last_exc or ValueError("No se pudo obtener respuesta del LLM")

            if not hasattr(plan_result, "steps") or plan_result.steps is None:
                raise ValueError(
                    "El LLM no devolvió los pasos en el formato esperado (faltan 'steps')"
                )

            # Cachear plan exitoso (TTL 1h)
            try:
                _plan_json = _json.dumps(
                    {
                        "steps": [
                            {
                                "agent": s.agent,
                                "action": s.action,
                                "instruction": s.instruction,
                                "needs_output_from": getattr(s, "needs_output_from", []) or [],
                            }
                            for s in plan_result.steps
                        ]
                    }
                )
                await llm_cache.set(_tenant_id, _plan_cache_key, _plan_json, ttl_override=3600)
            except Exception:
                logger.debug("Error guardando plan en caché", exc_info=True)

            plan: list[SubTask] = []
            for idx, step in enumerate(plan_result.steps):
                agent = step.agent if step.agent in VALID_DOMAINS else "unknown"
                raw_deps = getattr(step, "needs_output_from", None) or []
                deps = [f"step_{d}" for d in raw_deps if isinstance(d, int) and 1 <= d <= idx]
                plan.append(
                    {
                        "id": f"step_{idx + 1}",
                        "agent": agent,
                        "action": step.action,
                        "params": {"intent": step.instruction},
                        "depends_on": deps,
                        "status": "pending",
                    }
                )
        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}"
            logger.exception("Error planificando tarea")
            return {
                **state,
                "plan": [],
                "status": TaskStatus.FAILED,
                "error_message": f"Error planificando tarea: {err_msg}",
                "iteration_count": state["iteration_count"] + 1,
            }
    else:
        plan: list[SubTask] = [
            {
                "id": "step_1",
                "agent": domain,
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


# ─── Nodo: validación pre-ejecución ─────────────────────────────────────────


async def validate_node(state: OrchestratorState) -> OrchestratorState:
    """
    Validación determinista pre-ejecución.
    Verifica que el plan es ejecutable antes de invocar ningún agente o LLM.
    """
    plan = state.get("plan", [])
    if not plan:
        return {
            **state,
            "status": TaskStatus.FAILED,
            "error_message": "El plan está vacío tras la fase de planificación",
        }

    # Fail fast: agentes inválidos no deben llegar a dispatch
    invalid = [
        s["id"]
        for s in plan
        if s.get("agent") not in VALID_DOMAINS and s.get("agent") != "node_engine"
    ]
    if invalid:
        # Invalidar cache envenenado para que el próximo intento regenere el plan
        try:
            from app.services.llm_cache import llm_cache

            _tenant_id = state.get("tenant_id", "")
            _cache_key = f"plan:{state['user_intent']}"
            asyncio.create_task(llm_cache.invalidate(_tenant_id, _cache_key))
        except Exception as _e:
            logger.warning("Error invalidando caché de plan envenenado: %s", _e)
        return {
            **state,
            "status": TaskStatus.FAILED,
            "error_message": f"Plan contiene agentes no reconocidos: {invalid}",
        }

    return {
        **state,
        "status": TaskStatus.EXECUTING,
        "iteration_count": state["iteration_count"] + 1,
    }


# ─── Nodo: dispatch (invoca agentes) ────────────────────────────────────────


async def dispatch_node(state: OrchestratorState) -> OrchestratorState:
    """
    Invoca agentes especializados. Ejecuta en paralelo los pasos cuyas dependencias
    están resueltas. Usa ExecutionContext para enriquecer la intención con resultados previos.
    """
    from app.db.base import AsyncSessionLocal
    from app.services.audit import log_action

    # Guard: timeout global de tarea (máx 10 min)
    _MAX_TASK_SECONDS = 600
    _started_at = (state.get("additional_metadata") or {}).get("started_at")
    if _started_at:
        try:
            _elapsed = (datetime.now(UTC) - datetime.fromisoformat(_started_at)).total_seconds()
            if _elapsed > _MAX_TASK_SECONDS:
                logger.error(
                    "[ORCHESTRATOR] Tarea cancelada por timeout global: %.0fs > %ds",
                    _elapsed,
                    _MAX_TASK_SECONDS,
                )
                return {
                    **state,
                    "status": TaskStatus.FAILED,
                    "error_message": f"Tarea cancelada: superó el tiempo máximo de {_MAX_TASK_SECONDS}s (transcurridos {_elapsed:.0f}s)",
                }
        except Exception as _e:
            logger.warning("Error parseando started_at para timeout global: %s", _e)

    plan = state["plan"]
    updated_plan = list(plan)
    new_results = list(state["agent_results"])

    # Conjuntos de pasos resueltos para resolver dependencias
    resolved_ids = {s["id"] for s in plan if s.get("status") in ("done", "failed")}
    failed_ids = {s["id"] for s in plan if s.get("status") == "failed"}

    # Clasificar pasos pendientes: skip (deps fallidas), ready (deps resueltas), blocked (deps pendientes)
    ready: list[tuple[int, dict]] = []
    for idx, step in enumerate(plan):
        if step.get("status") != "pending":
            continue
        deps = step.get("depends_on", [])
        dep_failed = [d for d in deps if d in failed_ids]
        if dep_failed:
            logger.warning(
                "[ORCHESTRATOR] Omitiendo paso '%s' (%s): dependencias fallidas %s",
                step["id"],
                step["agent"],
                dep_failed,
            )
            updated_plan[idx] = {**step, "status": "failed"}
            new_results.append(
                {
                    "subtask_id": step["id"],
                    "agent": step["agent"],
                    "success": False,
                    "output": {
                        "action": "skipped",
                        "message": f"Paso omitido: dependencias fallidas ({', '.join(dep_failed)})",
                    },
                    "summary": "Paso omitido por dependencias fallidas",
                    "error": f"Dependencias fallidas: {', '.join(dep_failed)}",
                }
            )
            continue
        if all(d in resolved_ids for d in deps):
            ready.append((idx, step))

    # Si no hay pasos listos → DONE o deadlock
    if not ready:
        pending = [s for s in updated_plan if s.get("status") == "pending"]
        if pending:
            return {
                **state,
                "plan": updated_plan,
                "agent_results": new_results,
                "status": TaskStatus.FAILED,
                "error_message": "Deadlock: pasos pendientes con dependencias no resolubles",
                "iteration_count": state["iteration_count"] + 1,
            }
        return {
            **state,
            "plan": updated_plan,
            "agent_results": new_results,
            "status": TaskStatus.DONE,
            "iteration_count": state["iteration_count"] + 1,
        }

    # Contexto compartido para todos los pasos paralelos (resultados previos)
    try:
        from app.services.execution_context import ExecutionContext

        exec_ctx = ExecutionContext.from_state(state)
    except Exception as e:
        logger.warning("Error construyendo ExecutionContext: %s", e)
        exec_ctx = None

    # Errores transitorios que merecen un retry automático
    _TRANSIENT_ERRORS = (asyncio.TimeoutError, ConnectionError, OSError)

    async def _invoke_dispatcher(
        enriched_state: dict, subtask: dict, agent_name: str
    ) -> AgentResult:
        """Invoca el dispatcher con routing: DISPATCHER_MAP → AIEmployee dinámico → skill → fallback."""
        # 1. Dispatcher estático (agentes built-in)
        dispatcher_fn = DISPATCHER_MAP.get(agent_name)
        if dispatcher_fn:
            return await asyncio.wait_for(
                dispatcher_fn(enriched_state, subtask),
                timeout=120,
            )

        # 2. Skill routing
        if agent_name == "skill" or (
            isinstance(agent_name, str) and agent_name.startswith("skill:")
        ):
            from app.agents.orchestrator.dispatchers import _dispatch_skill

            return await _dispatch_skill(enriched_state, subtask)

        # 3. AIEmployee dinámico — busca un empleado IA activo para este dominio/tenant
        tenant_id = enriched_state.get("tenant_id")
        if tenant_id:
            try:
                result = await _invoke_dynamic_employee(
                    enriched_state,
                    subtask,
                    agent_name,
                    tenant_id,
                )
                if result is not None:
                    return result
            except Exception as e:
                logger.warning("Error en dynamic employee routing para '%s': %s", agent_name, e)

        # 4. Fallback — dominio sin dispatcher ni AIEmployee
        return {
            "subtask_id": subtask["id"],
            "agent": agent_name,
            "success": True,
            "output": {"message": f"[PENDIENTE] Agente '{agent_name}' no implementado aún"},
            "error": None,
        }

    async def _invoke_dynamic_employee(
        enriched_state: dict,
        subtask: dict,
        agent_name: str,
        tenant_id: str,
    ) -> AgentResult | None:
        """Busca un AIEmployee activo para el dominio y lo ejecuta vía compile_dynamic_agent.

        Returns None si no hay employee disponible (para que el caller use el fallback).
        """
        from uuid import UUID

        from sqlalchemy import select

        from app.agents.budget_guard import check_agent_budget
        from app.agents.custom_worker_agent import compile_dynamic_agent
        from app.db.base import AsyncSessionLocal
        from app.db.models.ai_employees import AIEmployee
        from app.services.activity_service import log_activity

        async with AsyncSessionLocal() as db:
            # Para agentes custom, priorizar el employee_id específico de la metadata
            addressed_id = (enriched_state.get("additional_metadata") or {}).get(
                "addressed_employee_id"
            )
            if addressed_id and agent_name == "custom":
                try:
                    emp_result = await db.execute(
                        select(AIEmployee).where(
                            AIEmployee.id == UUID(addressed_id),
                            AIEmployee.tenant_id == UUID(tenant_id),
                            AIEmployee.status.in_(["idle", "working", "pending_setup"]),
                        )
                    )
                    employee = emp_result.scalar_one_or_none()
                except Exception:
                    employee = None
            else:
                emp_result = await db.execute(
                    select(AIEmployee)
                    .where(
                        AIEmployee.tenant_id == UUID(tenant_id),
                        AIEmployee.domain == agent_name,
                        AIEmployee.status.in_(["idle", "working"]),
                    )
                    .limit(1)
                )
                employee = emp_result.scalar_one_or_none()
            if not employee:
                return None

            # Budget check
            has_budget = await check_agent_budget(str(employee.id), db)
            if not has_budget:
                return {
                    "subtask_id": subtask["id"],
                    "agent": agent_name,
                    "success": False,
                    "output": {"action": "budget_exceeded"},
                    "error": f"Empleado IA '{employee.name}' pausado por presupuesto agotado.",
                }

            # Mark as working
            employee.status = "working"
            await db.commit()

            try:
                graph = await compile_dynamic_agent(str(employee.id), db)
                intent = (
                    subtask.get("params", {}).get("intent")
                    or enriched_state.get("current_intent")
                    or enriched_state.get("user_intent", "")
                )

                result_state = await asyncio.wait_for(
                    graph.ainvoke(
                        {
                            "tenant_id": tenant_id,
                            "task_id": enriched_state.get("task_id"),
                            "user_id": enriched_state.get("user_id"),
                            "user_intent": intent,
                            "current_intent": intent,
                            "messages": [],
                            "agent_results": [],
                            "status": "running",
                        }
                    ),
                    timeout=120,
                )

                # Extract final text
                messages = result_state.get("messages", [])
                final_text = ""
                for msg in reversed(messages):
                    if (
                        hasattr(msg, "content")
                        and isinstance(msg.content, str)
                        and msg.content.strip()
                    ):
                        final_text = msg.content
                        break

                success = not final_text.lower().startswith("error")

                # Log activity
                try:
                    await log_activity(
                        db=db,
                        tenant_id=tenant_id,
                        employee_id=str(employee.id),
                        category=agent_name,
                        message=f"Ejecutó tarea: {final_text[:200]}",
                    )
                except Exception:
                    pass

                employee.status = "idle"
                await db.commit()

                return {
                    "subtask_id": subtask["id"],
                    "agent": agent_name,
                    "success": success,
                    "output": {
                        "action": "completed" if success else "failed",
                        "response": final_text,
                    },
                    "error": None if success else final_text,
                }

            except Exception as e:
                employee.status = "idle"
                await db.commit()
                logger.exception("Error en dynamic employee '%s'", employee.name)
                return {
                    "subtask_id": subtask["id"],
                    "agent": agent_name,
                    "success": False,
                    "output": {"action": "failed", "error": str(e)},
                    "error": str(e),
                }

    async def _execute_one(idx: int, subtask: dict) -> tuple[int, dict, AgentResult]:
        """Ejecuta un paso individual con retry para errores transitorios."""
        agent_name = subtask["agent"]

        # Enriquecer intent con contexto de pasos anteriores
        step_instruction = subtask.get("params", {}).get("intent")
        if exec_ctx:
            try:
                enriched = exec_ctx.build_enriched_intent(current_instruction=step_instruction)
            except Exception as _e:
                logger.warning("Error enriqueciendo intent con ExecutionContext: %s", _e)
                enriched = step_instruction or state.get("current_intent") or state["user_intent"]
        else:
            enriched = step_instruction or state.get("current_intent") or state["user_intent"]
        enriched_state = {**state, "current_intent": enriched}

        for attempt in range(2):  # 1 intento original + 1 retry
            try:
                result = await _invoke_dispatcher(enriched_state, subtask, agent_name)
                return idx, subtask, result
            except asyncio.TimeoutError:
                if attempt == 0:
                    logger.warning(
                        "[ORCHESTRATOR] Timeout en agente '%s', reintentando (1/1)...", agent_name
                    )
                    await asyncio.sleep(2)
                    continue
                result = {
                    "subtask_id": subtask["id"],
                    "agent": agent_name,
                    "success": False,
                    "output": {
                        "action": "timeout",
                        "error": f"El agente '{agent_name}' no respondió en 120 segundos (2 intentos)",
                    },
                    "summary": f"Timeout: agente {agent_name} excedió 120s tras 2 intentos",
                    "error": f"Timeout: el agente '{agent_name}' no respondió en 120s (2 intentos)",
                }
            except _TRANSIENT_ERRORS as e:
                err_str = str(e)
                is_rate_limit = (
                    "429" in err_str or "rate" in err_str.lower() or "quota" in err_str.lower()
                )
                if attempt == 0 and (isinstance(e, (ConnectionError, OSError)) or is_rate_limit):
                    wait = 5 if is_rate_limit else 2
                    logger.warning(
                        "[ORCHESTRATOR] Error transitorio en '%s': %s. Reintentando en %ds...",
                        agent_name,
                        type(e).__name__,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                result = {
                    "subtask_id": subtask["id"],
                    "agent": agent_name,
                    "success": False,
                    "output": {"action": "failed", "error": f"{type(e).__name__}: {e}"},
                    "summary": f"Error transitorio en agente {agent_name} tras retry: {e}",
                    "error": str(e),
                }
            except Exception as e:
                logger.exception("Excepción no controlada en dispatcher '%s'", agent_name)
                result = {
                    "subtask_id": subtask["id"],
                    "agent": agent_name,
                    "success": False,
                    "output": {"action": "failed", "error": f"{type(e).__name__}: {e}"},
                    "summary": f"Error inesperado en agente {agent_name}: {e}",
                    "error": str(e),
                }
                break  # No retry para errores no transitorios

        return idx, subtask, result

    # Ejecutar pasos listos — en paralelo si hay más de uno
    if len(ready) == 1:
        gathered = [await _execute_one(*ready[0])]
    else:
        logger.info(
            "[ORCHESTRATOR] Ejecutando %d pasos en paralelo: %s",
            len(ready),
            [s["id"] for _, s in ready],
        )
        gathered = list(await asyncio.gather(*[_execute_one(idx, step) for idx, step in ready]))

    # Procesar resultados, emitir audit/broadcast, y recopilar tareas de audit
    has_critical_failure = False
    critical_error = None
    has_approval = False
    approval_results: list[AgentResult] = []
    _audit_tasks: list[asyncio.Task] = []

    for idx, subtask, result in gathered:
        agent_name = subtask["agent"]
        new_results.append(result)
        updated_plan[idx] = {**subtask, "status": "done" if result["success"] else "failed"}

        # --- Audit log (recopilado, no fire-and-forget) ---
        action_str = (
            result.get("output", {}).get("action", "unknown_action")
            if result.get("output")
            else "unknown_action"
        )

        async def _safe_log(
            _result=result, _subtask=subtask, _agent=agent_name, _action=action_str
        ):
            async with AsyncSessionLocal() as db:
                await log_action(
                    db,
                    tenant_id=uuid.UUID(state["tenant_id"]),
                    task_id=uuid.UUID(state["task_id"]) if state.get("task_id") else None,
                    agent_name=_agent,
                    action_type=_action,
                    status="success" if _result["success"] else "failed",
                    input_data={"subtask": _subtask},
                    output_data=_result.get("output"),
                    error_detail=_result.get("error"),
                )
                await db.commit()

        _audit_tasks.append(asyncio.create_task(_safe_log()))

        # --- Broadcast WebSocket (fire-and-forget — no crítico) ---
        async def _broadcast(_result=result, _agent=agent_name, _step_num=idx + 1):
            try:
                from app.api.ws.notifications import manager as ws_manager

                await ws_manager.broadcast_to_tenant(
                    state["tenant_id"],
                    {
                        "type": "task_progress",
                        "task_id": state["task_id"],
                        "step": _step_num,
                        "total_steps": len(plan),
                        "agent": _agent,
                        "summary": _result.get("summary", ""),
                        "success": _result["success"],
                    },
                )
            except Exception as _ws_err:
                logger.debug("[WS] No se pudo emitir progreso: %s", _ws_err)

        _bc_task = asyncio.create_task(_broadcast())
        _bc_task.add_done_callback(
            lambda t: (
                logger.debug("[WS] Broadcast error: %s", t.exception())
                if not t.cancelled() and t.exception()
                else None
            )
        )

        # Comprobar aprobación humana (puede haber varias en paralelo)
        if result.get("output", {}).get("action") == "approval_required":
            has_approval = True
            approval_results.append(result)

        # Comprobar fallo crítico — el paso puede marcarse como no-crítico en el plan
        if not result["success"]:
            _default_non_critical = {"excel", "documents"}
            is_non_critical = (
                subtask.get("critical") is False or agent_name in _default_non_critical
            )
            if is_non_critical:
                logger.warning(
                    "[ORCHESTRATOR] Agente no crítico '%s' falló, continuando.", agent_name
                )
                # Inyectar aviso para que summarize_node informe al usuario
                new_results.append(
                    {
                        "subtask_id": f"{subtask['id']}_warning",
                        "agent": "system",
                        "success": True,
                        "output": {
                            "action": "partial_failure_warning",
                            "response": f"Aviso: el paso '{agent_name}' no se completó ({result.get('error', 'error desconocido')}). El resto de la tarea se ejecutó correctamente.",
                        },
                        "summary": f"Fallo parcial en {agent_name}",
                        "error": None,
                    }
                )
            else:
                has_critical_failure = True
                critical_error = result.get("error")

    # Determinar estado siguiente
    # Esperar a que los audit logs se escriban (máx 5s) antes de devolver estado
    if _audit_tasks:
        done, pending = await asyncio.wait(_audit_tasks, timeout=5)
        for t in pending:
            logger.warning("[ORCHESTRATOR] Audit log no completó en 5s, dejando en background")
        for t in done:
            if t.exception():
                logger.error("Error en audit log: %s", t.exception())

    next_pending = next(
        (i for i, s in enumerate(updated_plan) if s.get("status") == "pending"), len(updated_plan)
    )

    if has_approval:
        # Usar la primera aprobación; si hay múltiples, las demás quedan en agent_results
        first_approval = approval_results[0]
        if len(approval_results) > 1:
            logger.warning(
                "[ORCHESTRATOR] %d pasos requieren aprobación simultánea — pausando en la primera",
                len(approval_results),
            )
        return {
            **state,
            "plan": updated_plan,
            "agent_results": new_results,
            "current_step": next_pending,
            "status": TaskStatus.AWAITING_APPROVAL,
            "requires_human_approval": True,
            "approval_id": first_approval["output"].get("approval_id"),
            "iteration_count": state["iteration_count"] + 1,
        }

    if has_critical_failure:
        return {
            **state,
            "plan": updated_plan,
            "agent_results": new_results,
            "current_step": next_pending,
            "status": TaskStatus.FAILED,
            "error_message": critical_error,
            "iteration_count": state["iteration_count"] + 1,
        }

    new_status = TaskStatus.DONE if next_pending >= len(updated_plan) else TaskStatus.EXECUTING
    return {
        **state,
        "plan": updated_plan,
        "agent_results": new_results,
        "current_step": next_pending,
        "status": new_status,
        "iteration_count": state["iteration_count"] + 1,
    }


# ─── Nodo: resumen conversacional ─────────────────────────────────────────


async def summarize_node(state: OrchestratorState) -> dict:
    """
    Genera un resumen en lenguaje natural de los resultados de los agentes.
    Se salta si el dominio es 'chat' (ya devuelve texto conversacional).
    """
    # No resumir si es chat directo o si falló
    if state.get("classified_domain") == "chat":
        return state
    if state.get("status") != TaskStatus.DONE:
        return state

    results = state.get("agent_results", [])
    if not results:
        return state

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.core.llm_factory import get_llm

        # Construir resumen de los resultados de cada agente
        results_text = []
        for r in results:
            agent = r.get("agent", "?")
            output = r.get("output", {})
            response = output.get("response", "") or output.get("message", "")
            summary = r.get("summary", "")
            text = response if response else summary
            if text:
                results_text.append(f"[{agent}]: {text[:500]}")

        if not results_text:
            return state

        prompt = (
            "Eres el asistente de AutomatizaPyme. El usuario pidió lo siguiente:\n"
            f'"{state["user_intent"]}"\n\n'
            "Los agentes han devuelto estos resultados:\n" + "\n".join(results_text) + "\n\n"
            "Genera un RESUMEN EJECUTIVO breve y claro en español para el usuario. "
            "Usa lenguaje natural, no técnico. Si hay acciones urgentes, destácalas. "
            "Formato: texto directo, usa listas si mejora la legibilidad."
        )

        llm = get_llm(temperature=0.3)
        response = await asyncio.wait_for(
            llm.ainvoke(
                [
                    SystemMessage(
                        content="Resumes resultados de agentes ERP para PYMEs españolas. Sé conciso y directo."
                    ),
                    HumanMessage(content=prompt),
                ]
            ),
            timeout=30,
        )

        summary_text = response.content.strip() if response.content else ""
        if summary_text:
            summary_result: AgentResult = {
                "subtask_id": "summary",
                "agent": "summary",
                "success": True,
                "output": {"action": "chat_response", "response": summary_text},
                "summary": summary_text[:200],
                "error": None,
            }
            return {
                **state,
                "agent_results": list(results) + [summary_result],
            }
    except Exception as e:
        logger.warning("Error generando resumen conversacional: %s", e)

    return state
