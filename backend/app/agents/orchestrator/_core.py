"""
Orquestador central basado en LangGraph.
Implementa el grafo de estado: Classify → LoadKnowledge → Plan → Validate → Dispatch → Result

Los dispatchers, clasificador, utilidades y helpers se importan de módulos dedicados.
"""
import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.orchestrator.state import (
    AgentResult,
    MAX_ITERATIONS,
    OrchestratorState,
    SubTask,
    TaskStatus,
    VALID_DOMAINS,
)
from app.agents.orchestrator.classifier import classify_node
from app.agents.orchestrator.utils import _format_summary
from app.agents.orchestrator.dispatchers import DISPATCHER_MAP

logger = logging.getLogger(__name__)


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
                {"key": f.key, "value": f.value, "category": f.category}
                for f in facts
            ]
            return {"tenant_knowledge": knowledge_list}
    except Exception as e:
        logger.warning(f"Error cargando conocimiento: {e}")
        return {"tenant_knowledge": []}


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
                        logger.info(f"[PLAN] Workflow '{wf.name}' tiene nodos avanzados → delegando a NodeEngine")
                        execution_id = (state.get("additional_metadata") or {}).get("execution_id")
                        if execution_id:
                            try:
                                from app.services.task_dispatch import dispatch_node_engine
                                await dispatch_node_engine(execution_id)
                            except Exception as ce:
                                logger.error(f"[PLAN] Error lanzando NodeEngine: {ce}")
                        return {
                            "plan": [{"id": "node_engine", "agent": "node_engine", "action": "delegated", "params": {}, "depends_on": [], "status": "done"}],
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
                        node_intent = raw if (raw and len(raw.split()) > 3) else state["user_intent"]

                        plan.append({
                            "id": node_id,
                            "agent": data.get("domain", "coordinator"),
                            "action": "execute_node",
                            "params": {"intent": node_intent, "original_node_id": node_id},
                            "depends_on": final_deps,
                            "status": "pending",
                        })

                    if plan:
                        return {"plan": plan, "status": TaskStatus.EXECUTING}
        except Exception as e:
            logger.warning(f"[PLAN] Error cargando blueprint: {e}. Cayendo a planificación estándar.")

    domain = state["classified_domain"]

    if domain == "coordinator":
        try:
            from pydantic import BaseModel, Field

            class PlanStep(BaseModel):
                agent: str = Field(description="Dominios válidos: hr, crm, excel, email, billing, documents, banking, rag")
                action: str = Field(description="Acción corta, ej: extract_data, create_report, send_email")
                instruction: str = Field(description="Instrucción muy detallada en español para el agente actual que ejecutará el paso.")
                needs_output_from: list[int] = Field(default_factory=list, description="Índices (1-based) de pasos anteriores cuyo resultado necesita este paso. Vacío = independiente.")

            class MultiAgentPlan(BaseModel):
                steps: list[PlanStep] = Field(description="Lista de pasos para resolver la tarea. Pasos sin dependencias se ejecutan en paralelo.")

            from app.core.config import settings
            from app.core.llm_factory import get_llm
            from app.services.llm_cache import llm_cache
            import json as _json

            # Consultar caché de planificación
            _tenant_id = state.get("tenant_id", "")
            _plan_cache_key = f"plan:{state['user_intent']}"
            _cached_plan = await llm_cache.get(_tenant_id, _plan_cache_key)
            if _cached_plan:
                try:
                    _cached_data = _json.loads(_cached_plan)
                    plan: list[SubTask] = []
                    for idx, step in enumerate(_cached_data.get("steps", [])):
                        raw_deps = step.get("needs_output_from", []) or []
                        deps = [f"step_{d}" for d in raw_deps if isinstance(d, int) and 1 <= d <= idx]
                        if not deps and idx > 0 and not raw_deps:
                            deps = [f"step_{idx}"]
                        plan.append({
                            "id": f"step_{idx+1}",
                            "agent": step.get("agent", "unknown"),
                            "action": step.get("action", "process"),
                            "params": {"intent": step.get("instruction", "")},
                            "depends_on": deps,
                            "status": "pending",
                        })
                    if plan:
                        return {"plan": plan, "status": TaskStatus.EXECUTING}
                except Exception:
                    pass  # Caché corrupto, continuar con LLM

            llm = get_llm(temperature=0)
            structured_llm = llm.with_structured_output(MultiAgentPlan, method="json_mode")

            prompt = (
                "Eres el asistente de gestión empresarial para PYMEs españolas.\n"
                "Conoces el Plan General Contable español (PGC 2007), la normativa de la AEAT, "
                "los tipos de IVA vigentes (general 21%, reducido 10%, superreducido 4%, exento 0%), "
                "el sistema de Seguridad Social español (contingencias comunes 4,70%, desempleo 1,55%, FP 0,10%, MEI 0,12%) "
                "y la legislación laboral del Estatuto de los Trabajadores.\n"
                "La empresa opera en euros (€) bajo ley española. Hoy es "
                + datetime.now().strftime("%d/%m/%Y") + ".\n\n"
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
                "- excel: generar archivo Excel (.xlsx) con datos de la empresa (facturas, empleados, clientes, nóminas, inventario, banco).\n\n"
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
                    plan_result = structured_llm.invoke(prompt)
                    break
                except Exception as _e:
                    last_exc = _e
                    err_str = str(_e)
                    # Si es error de cuota o servidor → fallback a Groq, luego OpenAI
                    if "ResourceExhausted" in type(_e).__name__ or "429" in err_str or "quota" in err_str.lower() or "500" in err_str:
                        if _attempt == 0 and settings.GROQ_API_KEY:
                            logger.warning(f"[PLAN] Gemini caído (HTTP {err_str[:50]}), intentando Groq...")
                            try:
                                _fallback_llm = get_llm(temperature=0, provider="groq")
                                structured_llm = _fallback_llm.with_structured_output(MultiAgentPlan, method="json_mode")
                                continue
                            except Exception:
                                pass
                        logger.warning("[PLAN] Fallback final al proveedor secundario.")
                        _fallback_llm = get_llm(temperature=0, provider="openai") if settings.OPENAI_API_KEY else get_llm(temperature=0)
                        structured_llm = _fallback_llm.with_structured_output(MultiAgentPlan, method="json_mode")
                        continue
                    # Si es error de red → esperar y reintentar
                    elif _attempt < 2:
                        await asyncio.sleep(5 * (_attempt + 1))
                    else:
                        raise

            if plan_result is None:
                raise last_exc or ValueError("No se pudo obtener respuesta del LLM")

            if not hasattr(plan_result, "steps") or plan_result.steps is None:
                raise ValueError("El LLM no devolvió los pasos en el formato esperado (faltan 'steps')")

            # Cachear plan exitoso (TTL 1h)
            try:
                _plan_json = _json.dumps({"steps": [
                    {"agent": s.agent, "action": s.action, "instruction": s.instruction,
                     "needs_output_from": getattr(s, "needs_output_from", []) or []}
                    for s in plan_result.steps
                ]})
                await llm_cache.set(_tenant_id, _plan_cache_key, _plan_json, ttl_override=3600)
            except Exception:
                pass  # No bloquear si el caché falla

            plan: list[SubTask] = []
            for idx, step in enumerate(plan_result.steps):
                agent = step.agent if step.agent in VALID_DOMAINS else "unknown"
                raw_deps = getattr(step, "needs_output_from", None) or []
                deps = [f"step_{d}" for d in raw_deps if isinstance(d, int) and 1 <= d <= idx]
                if not deps and idx > 0 and not raw_deps:
                    deps = [f"step_{idx}"]
                plan.append({
                    "id": f"step_{idx+1}",
                    "agent": agent,
                    "action": step.action,
                    "params": {"intent": step.instruction},
                    "depends_on": deps,
                    "status": "pending",
                })
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            # Fallback seguro
            plan = [{
                "id": "step_1",
                "agent": "unknown",
                "action": "process",
                "params": {"intent": f"Plan fallido: {str(e)}\n\n{err_msg} -> {state['user_intent']}"},
                "depends_on": [],
                "status": "pending",
            }]
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

    return {
        **state,
        "status": TaskStatus.EXECUTING,
        "iteration_count": state["iteration_count"] + 1,
    }


# ─── Nodo: dispatch (invoca agentes) ────────────────────────────────────────

async def dispatch_node(state: OrchestratorState) -> OrchestratorState:
    """
    Invoca el agente especializado correspondiente al dominio de la subtarea.
    Usa ExecutionContext para enriquecer la intención con los resultados previos.
    """
    from app.services.execution_context import ExecutionContext

    plan = state["plan"]
    current_step = state["current_step"]

    if current_step >= len(plan):
        return {**state, "status": TaskStatus.DONE}

    subtask = plan[current_step]
    agent_name = subtask["agent"]

    # Construir contexto enriquecido con la instrucción específica del paso y outputs anteriores
    ctx = ExecutionContext.from_state(state)
    enriched_intent = ctx.build_enriched_intent(
        current_instruction=subtask.get("params", {}).get("intent")
    )
    enriched_state = {**state, "current_intent": enriched_intent}

    result: AgentResult

    # Buscar dispatcher en el registro centralizado
    dispatcher_fn = DISPATCHER_MAP.get(agent_name)
    if dispatcher_fn:
        result = await dispatcher_fn(enriched_state, subtask)
    elif agent_name == "skill" or (isinstance(agent_name, str) and agent_name.startswith("skill:")):
        from app.agents.orchestrator.dispatchers import _dispatch_skill
        result = await _dispatch_skill(enriched_state, subtask)
    else:
        if agent_name == "unknown":
            intent_param = subtask.get("params", {}).get("intent", "")
            if "Plan fallido:" in intent_param:
                message = f"Error interno al planificar la tarea compleja: {intent_param}"
                error_msg = intent_param
            else:
                message = "No he podido entender tu solicitud. Por favor, especifica si quieres crear una factura, revisar un documento, etc."
                error_msg = "Comando no reconocido."
        else:
            message = f"[PENDIENTE] Agente '{agent_name}' no implementado aún"
            error_msg = None

        result = {
            "subtask_id": subtask["id"],
            "agent": agent_name,
            "success": False if agent_name == "unknown" else True,
            "output": {"message": message},
            "error": error_msg,
        }

    # --- REGISTRO DE AUDITORÍA INMUTABLE ---
    from app.db.base import AsyncSessionLocal
    from app.services.audit import log_action

    action_str = result.get("output", {}).get("action", "unknown_action") if result.get("output") else "unknown_action"

    async def _safe_log():
        async with AsyncSessionLocal() as db:
            await log_action(
                db,
                tenant_id=uuid.UUID(state["tenant_id"]),
                task_id=uuid.UUID(state["task_id"]) if state.get("task_id") else None,
                agent_name=agent_name,
                action_type=action_str,
                status="success" if result["success"] else "failed",
                input_data={"subtask": subtask},
                output_data=result.get("output"),
                error_detail=result.get("error")
            )
            await db.commit()

    # Fire and forget el log
    asyncio.create_task(_safe_log())

    # Emitir progreso en tiempo real al frontend vía WebSocket
    async def _broadcast_step():
        try:
            from app.api.ws.notifications import manager as ws_manager
            total_steps = len(plan)
            step_num = current_step + 1
            await ws_manager.broadcast_to_tenant(
                state["tenant_id"],
                {
                    "type": "task_progress",
                    "task_id": state["task_id"],
                    "step": step_num,
                    "total_steps": total_steps,
                    "agent": agent_name,
                    "summary": result.get("summary", ""),
                    "success": result["success"],
                }
            )
        except Exception as _ws_err:
            logger.debug(f"[WS] No se pudo emitir progreso: {_ws_err}")
    asyncio.create_task(_broadcast_step())
    # ----------------------------------------

    # Si el agente solicita aprobación humana, pausar el grafo
    if result.get("output", {}).get("action") == "approval_required":
        return {
            **state,
            "plan": plan,
            "agent_results": list(state["agent_results"]) + [result],
            "status": TaskStatus.AWAITING_APPROVAL,
            "requires_human_approval": True,
            "approval_id": result["output"].get("approval_id"),
            "iteration_count": state["iteration_count"] + 1,
        }

    new_results = list(state["agent_results"]) + [result]
    updated_plan = list(plan)
    updated_plan[current_step] = {**subtask, "status": "done" if result["success"] else "failed"}

    next_step = current_step + 1
    if not result["success"]:
        # Si el agente es "excel" o "documents" y falla, lo ignoramos y continuamos
        non_critical_agents = {"excel", "documents"}
        if agent_name in non_critical_agents:
            logger.warning(f"[ORCHESTRATOR] Agente no crítico '{agent_name}' falló, continuando con el siguiente paso.")
        else:
            return {
                **state,
                "plan": updated_plan,
                "agent_results": new_results,
                "status": TaskStatus.FAILED,
                "error_message": result.get("error"),
                "iteration_count": state["iteration_count"] + 1,
            }

    new_status = TaskStatus.DONE if next_step >= len(plan) else TaskStatus.EXECUTING
    return {
        **state,
        "plan": updated_plan,
        "agent_results": new_results,
        "current_step": next_step,
        "status": new_status,
        "iteration_count": state["iteration_count"] + 1,
    }


# ─── Routing functions ──────────────────────────────────────────────────────

def route_after_validate(state: OrchestratorState) -> str:
    if state["status"] == TaskStatus.FAILED:
        return "end"
    if state.get("requires_human_approval"):
        return "await_approval"
    return "dispatch"


def route_after_dispatch(state: OrchestratorState) -> str:
    if state["status"] == TaskStatus.FAILED:
        return "end"
    if state["status"] == TaskStatus.DONE:
        return "end"
    if state["status"] == TaskStatus.AWAITING_APPROVAL:
        return "end"  # Pausa: esperar aprobación humana antes de continuar
    if state["iteration_count"] >= MAX_ITERATIONS:
        return "end"
    return "dispatch"  # Continúa con siguiente subtarea


# ─── Construcción del grafo ───────────────────────────────────────────────────

def build_orchestrator() -> CompiledStateGraph:
    graph = StateGraph(OrchestratorState)

    graph.add_node("classify", classify_node)
    graph.add_node("load_knowledge", load_knowledge_node)
    graph.add_node("planner", plan_node)
    graph.add_node("validate", validate_node)
    graph.add_node("dispatch", dispatch_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "load_knowledge")
    graph.add_edge("load_knowledge", "planner")
    graph.add_edge("planner", "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "dispatch": "dispatch",
            "await_approval": END,
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "dispatch",
        route_after_dispatch,
        {
            "dispatch": "dispatch",
            "end": END,
        },
    )

    return graph.compile()


# Instancia global del orquestador compilado
orchestrator = build_orchestrator()
