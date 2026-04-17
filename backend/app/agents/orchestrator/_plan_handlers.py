"""Node handlers: plan_node and its helpers (_plan_from_blueprint, _plan_from_llm)."""

import asyncio
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
from app.db.models.models import Workflow
from app.services.llm_cache import llm_cache

logger = logging.getLogger(__name__)


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
