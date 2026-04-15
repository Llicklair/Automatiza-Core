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
import json
import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agents.orchestrator.dispatchers import DISPATCHER_MAP, _dispatch_skill
from app.agents.orchestrator.state import (
    MAX_ITERATIONS,
    VALID_DOMAINS,
    AgentResult,
    OrchestratorState,
    SubTask,
    TaskStatus,
)
from app.core.config import settings
from app.core.llm_factory import get_llm, get_llm_for_tenant, set_tenant_llm_context
from app.db.base import AsyncSessionLocal
from app.db.models.ai_employees import AIEmployee
from app.db.models.models import TenantKnowledge, TenantLlmConfig, Workflow
from app.services.audit import log_action
from app.services.encryption import decrypt_credentials
from app.services.execution_context import ExecutionContext
from app.services.llm_cache import llm_cache

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


# ─── Helpers de planificación ───────────────────────────────────────────────


async def _plan_from_blueprint(state: OrchestratorState, wf) -> "list[SubTask] | None":
    """
    Convierte ui_nodes de un Workflow en SubTasks.
    Devuelve None si el blueprint está vacío.
    Delega a NodeEngine si hay nodos avanzados (y devuelve plan marcado como done).
    """
    from app.services.ai.node_engine import has_advanced_nodes

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
        return [{"id": "node_engine", "agent": "node_engine", "action": "delegated",
                 "params": {}, "depends_on": [], "status": "done"}]

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
        plan.append({
            "id": node_id, "agent": data.get("domain", "coordinator"),
            "action": "execute_node",
            "params": {"intent": node_intent, "original_node_id": node_id},
            "depends_on": final_deps, "status": "pending",
        })
    return plan if plan else None


async def _plan_from_llm(state: OrchestratorState) -> "list[SubTask]":
    """Descompone la tarea via LLM con caché y fallback de proveedor."""
    class PlanStep(BaseModel):
        agent: str = Field(description="Dominios válidos: hr, crm, excel, email, billing, documents, banking, rag, team, custom")
        action: str = Field(description="Acción corta, ej: extract_data, create_report, send_email")
        instruction: str = Field(description="Instrucción muy detallada en español para el agente actual.")
        needs_output_from: list[int] = Field(default_factory=list, description="Índices (1-based) de pasos anteriores requeridos.")

    class MultiAgentPlan(BaseModel):
        steps: list[PlanStep] = Field(description="Lista de pasos para resolver la tarea.")

    _tenant_id = state.get("tenant_id", "")
    _cache_key = f"plan:{state['user_intent']}"

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
                plan.append({
                    "id": f"step_{idx + 1}", "agent": agent,
                    "action": step.get("action", "process"),
                    "params": {"intent": step.get("instruction", "")},
                    "depends_on": [f"step_{d}" for d in raw_deps if isinstance(d, int) and 1 <= d <= idx],
                    "status": "pending",
                })
            if plan and valid:
                return plan
            if not valid:
                try:
                    await llm_cache.invalidate(_tenant_id, _cache_key)
                except Exception:
                    pass
        except Exception:
            logger.debug("Caché de plan corrupto, continuando con LLM", exc_info=True)

    # Invocar LLM con retry y fallback de proveedor
    llm = get_llm(temperature=0)
    structured_llm = llm.with_structured_output(MultiAgentPlan, method="json_mode")
    prompt = (
        "Eres el asistente de gestión empresarial para PYMEs españolas.\n"
        "Conoces el PGC 2007, la normativa AEAT, tipos de IVA (21%/10%/4%/0%), "
        "Seguridad Social (CC 4,70%, desempleo 1,55%, FP 0,10%, MEI 0,12%) y el ET.\n"
        f"La empresa opera en euros bajo ley española. Hoy es {datetime.now().strftime('%d/%m/%Y')}.\n\n"
        "Descompón la petición en pasos MÍNIMOS usando SOLO los agentes necesarios. Ejecución puntual — NO crees reglas recurrentes.\n\n"
        f"Petición: {state['user_intent']}\n\n"
        "AGENTES: billing, hr, crm, banking, email, compliance, documents, rag, excel, custom\n"
        "REGLAS: mínimo de pasos; excel para hojas/informes; billing guarda facturas internamente; "
        "email como último paso si se pide notificación; NIF en facturas; mes/año en nóminas.\n"
        "PARALELISMO: needs_output_from con índices (1-based) de pasos requeridos; vacío = paralelo.\n\n"
        'JSON: {"steps": [{"agent": "...", "action": "...", "instruction": "...", "needs_output_from": []}]}'
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
            if ("ResourceExhausted" in type(exc).__name__ or "429" in err_str
                    or "quota" in err_str.lower() or "500" in err_str):
                if attempt == 0 and settings.GROQ_API_KEY:
                    logger.warning("[PLAN] Proveedor principal caído, intentando Groq...")
                    try:
                        structured_llm = get_llm(temperature=0, provider="groq").with_structured_output(MultiAgentPlan, method="json_mode")
                        continue
                    except Exception:
                        logger.debug("Fallback a Groq falló", exc_info=True)
                fallback_llm = get_llm(temperature=0, provider="openai") if settings.OPENAI_API_KEY else get_llm(temperature=0)
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
        await llm_cache.set(_tenant_id, _cache_key, json.dumps({
            "steps": [{"agent": s.agent, "action": s.action, "instruction": s.instruction,
                       "needs_output_from": getattr(s, "needs_output_from", []) or []}
                      for s in plan_result.steps]
        }), ttl_override=3600)
    except Exception:
        logger.debug("Error guardando plan en caché", exc_info=True)

    plan: list[SubTask] = []
    for idx, step in enumerate(plan_result.steps):
        agent = step.agent if step.agent in VALID_DOMAINS else "unknown"
        raw_deps = getattr(step, "needs_output_from", None) or []
        plan.append({
            "id": f"step_{idx + 1}", "agent": agent, "action": step.action,
            "params": {"intent": step.instruction},
            "depends_on": [f"step_{d}" for d in raw_deps if isinstance(d, int) and 1 <= d <= idx],
            "status": "pending",
        })
    return plan


# ─── Nodo: planificación ─────────────────────────────────────────────────────


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
                **state, "plan": [], "status": TaskStatus.FAILED,
                "error_message": f"Error planificando tarea: {type(e).__name__}: {e}",
                "iteration_count": state["iteration_count"] + 1,
            }
    # 3. Plan de un solo agente
    else:
        plan = [{"id": "step_1", "agent": domain, "action": "process",
                 "params": {"intent": state["user_intent"]}, "depends_on": [], "status": "pending"}]

    return {**state, "plan": plan, "status": TaskStatus.VALIDATING,
            "iteration_count": state["iteration_count"] + 1}


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


# ─── Helpers de dispatch ────────────────────────────────────────────────────

_TRANSIENT_ERRORS = (asyncio.TimeoutError, ConnectionError, OSError)


async def _invoke_dynamic_employee(
    enriched_state: dict,
    subtask: dict,
    agent_name: str,
    tenant_id: str,
) -> "AgentResult | None":
    """Busca un AIEmployee activo para el dominio y lo ejecuta vía compile_dynamic_agent.
    Devuelve None si no hay employee disponible."""
    from app.agents.workers import check_agent_budget, compile_dynamic_agent
    from app.services.workflow.activity import log_activity

    async with AsyncSessionLocal() as db:
        addressed_id = (enriched_state.get("additional_metadata") or {}).get("addressed_employee_id")
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

        has_budget = await check_agent_budget(str(employee.id), db)
        if not has_budget:
            return {
                "subtask_id": subtask["id"], "agent": agent_name, "success": False,
                "output": {"action": "budget_exceeded"},
                "error": f"Empleado IA '{employee.name}' pausado por presupuesto agotado.",
            }

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
                graph.ainvoke({
                    "tenant_id": tenant_id,
                    "task_id": enriched_state.get("task_id"),
                    "user_id": enriched_state.get("user_id"),
                    "user_intent": intent, "current_intent": intent,
                    "messages": [], "agent_results": [], "status": "running",
                }),
                timeout=120,
            )
            messages = result_state.get("messages", [])
            final_text = next(
                (msg.content for msg in reversed(messages)
                 if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip()),
                ""
            )
            success = not final_text.lower().startswith("error")
            try:
                await log_activity(db=db, tenant_id=tenant_id, employee_id=str(employee.id),
                                   category=agent_name, message=f"Ejecutó tarea: {final_text[:200]}")
            except Exception:
                pass
            employee.status = "idle"
            await db.commit()
            return {
                "subtask_id": subtask["id"], "agent": agent_name, "success": success,
                "output": {"action": "completed" if success else "failed", "response": final_text},
                "error": None if success else final_text,
            }
        except Exception as e:
            employee.status = "idle"
            await db.commit()
            logger.exception("Error en dynamic employee '%s'", employee.name)
            return {
                "subtask_id": subtask["id"], "agent": agent_name, "success": False,
                "output": {"action": "failed", "error": str(e)}, "error": str(e),
            }


async def _invoke_dispatcher(enriched_state: dict, subtask: dict, agent_name: str) -> AgentResult:
    """Routing: DISPATCHER_MAP → skill → AIEmployee dinámico → fallback."""
    dispatcher_fn = DISPATCHER_MAP.get(agent_name)
    if dispatcher_fn:
        return await asyncio.wait_for(dispatcher_fn(enriched_state, subtask), timeout=120)

    if agent_name == "skill" or (isinstance(agent_name, str) and agent_name.startswith("skill:")):
        return await _dispatch_skill(enriched_state, subtask)

    tenant_id = enriched_state.get("tenant_id")
    if tenant_id:
        try:
            result = await _invoke_dynamic_employee(enriched_state, subtask, agent_name, tenant_id)
            if result is not None:
                return result
        except Exception as e:
            logger.warning("Error en dynamic employee routing para '%s': %s", agent_name, e)

    return {
        "subtask_id": subtask["id"], "agent": agent_name, "success": True,
        "output": {"message": f"[PENDIENTE] Agente '{agent_name}' no implementado aún"},
        "error": None,
    }


async def _execute_one(
    idx: int, subtask: dict, state: dict, exec_ctx
) -> "tuple[int, dict, AgentResult]":
    """Ejecuta un paso individual con retry para errores transitorios."""
    agent_name = subtask["agent"]
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

    for attempt in range(2):
        try:
            result = await _invoke_dispatcher(enriched_state, subtask, agent_name)
            return idx, subtask, result
        except asyncio.TimeoutError:
            if attempt == 0:
                logger.warning("[ORCHESTRATOR] Timeout en agente '%s', reintentando (1/1)...", agent_name)
                await asyncio.sleep(2)
                continue
            result = {
                "subtask_id": subtask["id"], "agent": agent_name, "success": False,
                "output": {"action": "timeout", "error": f"El agente '{agent_name}' no respondió en 120s (2 intentos)"},
                "summary": f"Timeout: agente {agent_name} excedió 120s tras 2 intentos",
                "error": f"Timeout: el agente '{agent_name}' no respondió en 120s (2 intentos)",
            }
        except _TRANSIENT_ERRORS as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "rate" in err_str.lower() or "quota" in err_str.lower()
            if attempt == 0 and (isinstance(e, (ConnectionError, OSError)) or is_rate_limit):
                wait = 5 if is_rate_limit else 2
                logger.warning("[ORCHESTRATOR] Error transitorio en '%s': %s. Reintentando en %ds...",
                               agent_name, type(e).__name__, wait)
                await asyncio.sleep(wait)
                continue
            result = {
                "subtask_id": subtask["id"], "agent": agent_name, "success": False,
                "output": {"action": "failed", "error": f"{type(e).__name__}: {e}"},
                "summary": f"Error transitorio en agente {agent_name} tras retry: {e}",
                "error": str(e),
            }
        except Exception as e:
            logger.exception("Excepción no controlada en dispatcher '%s'", agent_name)
            result = {
                "subtask_id": subtask["id"], "agent": agent_name, "success": False,
                "output": {"action": "failed", "error": f"{type(e).__name__}: {e}"},
                "summary": f"Error inesperado en agente {agent_name}: {e}",
                "error": str(e),
            }
            break

    return idx, subtask, result


# ─── Nodo: dispatch (invoca agentes) ────────────────────────────────────────


async def dispatch_node(state: OrchestratorState) -> OrchestratorState:
    """
    Invoca agentes especializados. Ejecuta en paralelo los pasos cuyas dependencias
    están resueltas. Usa ExecutionContext para enriquecer la intención con resultados previos.
    """
    # Guard: timeout global de tarea (máx 10 min)
    _MAX_TASK_SECONDS = 600
    _started_at = (state.get("additional_metadata") or {}).get("started_at")
    if _started_at:
        try:
            _elapsed = (datetime.now(UTC) - datetime.fromisoformat(_started_at)).total_seconds()
            if _elapsed > _MAX_TASK_SECONDS:
                logger.error("[ORCHESTRATOR] Tarea cancelada por timeout global: %.0fs > %ds", _elapsed, _MAX_TASK_SECONDS)
                return {
                    **state, "status": TaskStatus.FAILED,
                    "error_message": f"Tarea cancelada: superó el tiempo máximo de {_MAX_TASK_SECONDS}s (transcurridos {_elapsed:.0f}s)",
                }
        except Exception as _e:
            logger.warning("Error parseando started_at para timeout global: %s", _e)

    plan = state["plan"]
    updated_plan = list(plan)
    new_results = list(state["agent_results"])
    resolved_ids = {s["id"] for s in plan if s.get("status") in ("done", "failed")}
    failed_ids = {s["id"] for s in plan if s.get("status") == "failed"}

    ready: list[tuple[int, dict]] = []
    for idx, step in enumerate(plan):
        if step.get("status") != "pending":
            continue
        deps = step.get("depends_on", [])
        dep_failed = [d for d in deps if d in failed_ids]
        if dep_failed:
            logger.warning("[ORCHESTRATOR] Omitiendo paso '%s' (%s): dependencias fallidas %s",
                           step["id"], step["agent"], dep_failed)
            updated_plan[idx] = {**step, "status": "failed"}
            new_results.append({
                "subtask_id": step["id"], "agent": step["agent"], "success": False,
                "output": {"action": "skipped", "message": f"Paso omitido: dependencias fallidas ({', '.join(dep_failed)})"},
                "summary": "Paso omitido por dependencias fallidas",
                "error": f"Dependencias fallidas: {', '.join(dep_failed)}",
            })
            continue
        if all(d in resolved_ids for d in deps):
            ready.append((idx, step))

    if not ready:
        pending = [s for s in updated_plan if s.get("status") == "pending"]
        if pending:
            return {**state, "plan": updated_plan, "agent_results": new_results,
                    "status": TaskStatus.FAILED,
                    "error_message": "Deadlock: pasos pendientes con dependencias no resolubles",
                    "iteration_count": state["iteration_count"] + 1}
        return {**state, "plan": updated_plan, "agent_results": new_results,
                "status": TaskStatus.DONE, "iteration_count": state["iteration_count"] + 1}

    try:
        exec_ctx = ExecutionContext.from_state(state)
    except Exception as e:
        logger.warning("Error construyendo ExecutionContext: %s", e)
        exec_ctx = None

    if len(ready) == 1:
        gathered = [await _execute_one(*ready[0], state, exec_ctx)]
    else:
        logger.info("[ORCHESTRATOR] Ejecutando %d pasos en paralelo: %s",
                    len(ready), [s["id"] for _, s in ready])
        gathered = list(await asyncio.gather(*[_execute_one(idx, step, state, exec_ctx) for idx, step in ready]))

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
