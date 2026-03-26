"""
Dispatcher de chat — responde preguntas generales y consultas de estado
sin invocar agentes especializados. Usa el LLM directamente con contexto del tenant.
"""
import logging
from datetime import datetime

from app.agents.orchestrator.state import AgentResult, OrchestratorState

logger = logging.getLogger(__name__)

_CHAT_SYSTEM = """\
Eres el asistente de AutomatizaPyme, un ERP inteligente para PYMEs españolas.
Respondes preguntas generales, dudas conceptuales y consultas de estado de forma clara y concisa.
Hoy es {date}. Responde siempre en español.

CONTEXTO DEL TENANT:
{tenant_context}

{extra_context}

REGLAS:
- Sé directo y útil. No uses jerga técnica innecesaria.
- Si te preguntan por el estado de una tarea, usa el contexto proporcionado.
- Si no tienes información suficiente para responder, dilo honestamente.
- No inventes datos. Si no sabes algo, sugiere qué acción podría hacer el usuario para obtenerlo.
- Respuestas cortas y al grano. Usa listas cuando mejore la legibilidad.
- NUNCA sugieras al usuario crear tareas desde la sección de automatizaciones ni automatizaciones desde la sección de tareas. Son módulos independientes: las tareas se crean en /tareas y las automatizaciones en /automatizaciones. No mezcles funcionalidades entre módulos.
- Tú solo respondes preguntas y consultas. No ejecutas acciones ni creas nada."""


async def _dispatch_chat(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Responde directamente al usuario usando el LLM con contexto del tenant."""
    intent = subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"]))
    tenant_id = state["tenant_id"]

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.core.llm_factory import get_llm

        # Construir contexto del tenant
        tenant_context = _build_tenant_context(state)

        # Contexto extra según metadata (ej: workflows desde /automatizaciones)
        extra_context = await _build_extra_context(state)

        system_prompt = _CHAT_SYSTEM.format(
            date=datetime.now().strftime("%d/%m/%Y"),
            tenant_context=tenant_context,
            extra_context=extra_context,
        )

        llm = get_llm(temperature=0.3)
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=intent),
        ])

        response_text = response.content.strip() if response.content else "No he podido generar una respuesta."

        return {
            "subtask_id": subtask["id"],
            "agent": "chat",
            "success": True,
            "output": {"action": "chat_response", "response": response_text},
            "summary": response_text[:200],
            "error": None,
        }

    except Exception as e:
        logger.exception("Error en dispatcher chat")
        return {
            "subtask_id": subtask["id"],
            "agent": "chat",
            "success": False,
            "output": {"action": "failed", "response": f"Error al procesar tu pregunta: {e}"},
            "summary": f"Error en chat: {e}",
            "error": str(e),
        }


def _build_tenant_context(state: OrchestratorState) -> str:
    """Construye contexto a partir del tenant_knowledge cargado."""
    knowledge = state.get("tenant_knowledge", [])
    if not knowledge:
        return "No hay información adicional del tenant disponible."

    lines = []
    for fact in knowledge:
        lines.append(f"- {fact.get('key', '')}: {fact.get('value', '')}")
    return "\n".join(lines)


async def _build_extra_context(state: OrchestratorState) -> str:
    """Carga contexto adicional según metadata (workflows, tareas recientes, etc.)."""
    metadata = state.get("additional_metadata") or {}
    context_type = metadata.get("context")
    tenant_id = state.get("tenant_id")
    parts = []

    if context_type == "workflows" and tenant_id:
        parts.append(await _load_workflow_context(tenant_id))

    # Siempre cargar tareas recientes para consultas de estado
    if tenant_id:
        parts.append(await _load_recent_tasks_context(tenant_id))

    return "\n\n".join(p for p in parts if p)


async def _load_workflow_context(tenant_id: str) -> str:
    """Carga resumen de workflows y últimas ejecuciones."""
    try:
        from uuid import UUID
        from sqlalchemy import select, desc
        from app.db.base import AsyncSessionLocal
        from app.db.models.models import Workflow, WorkflowExecution

        async with AsyncSessionLocal() as db:
            wf_result = await db.execute(
                select(Workflow)
                .where(Workflow.tenant_id == UUID(tenant_id))
                .order_by(desc(Workflow.created_at))
                .limit(20)
            )
            workflows = wf_result.scalars().all()

            if not workflows:
                return "AUTOMATIZACIONES: No hay automatizaciones configuradas."

            lines = ["AUTOMATIZACIONES CONFIGURADAS:"]
            for wf in workflows:
                status = "activa" if wf.is_active else "pausada"
                lines.append(f"- '{wf.name}' ({status}) — trigger: {wf.trigger_type}, modo: {wf.execution_mode}")

            # Últimas 10 ejecuciones
            wf_ids = [wf.id for wf in workflows]
            exec_result = await db.execute(
                select(WorkflowExecution)
                .where(WorkflowExecution.workflow_id.in_(wf_ids))
                .order_by(desc(WorkflowExecution.started_at))
                .limit(10)
            )
            execs = exec_result.scalars().all()

            if execs:
                lines.append("\nULTIMAS EJECUCIONES:")
                for ex in execs:
                    wf_name = next((w.name for w in workflows if w.id == ex.workflow_id), "?")
                    lines.append(f"- '{wf_name}' — {ex.status} ({ex.started_at.strftime('%d/%m %H:%M') if ex.started_at else '?'})")

            return "\n".join(lines)
    except Exception as e:
        logger.debug("Error cargando contexto de workflows: %s", e)
        return ""


async def _load_recent_tasks_context(tenant_id: str) -> str:
    """Carga las últimas tareas para consultas de estado."""
    try:
        from uuid import UUID
        from sqlalchemy import select, desc
        from app.db.base import AsyncSessionLocal
        from app.db.models.models import Task

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Task)
                .where(Task.tenant_id == UUID(tenant_id))
                .order_by(desc(Task.created_at))
                .limit(10)
            )
            tasks = result.scalars().all()

            if not tasks:
                return "TAREAS RECIENTES: No hay tareas registradas."

            lines = ["TAREAS RECIENTES:"]
            for t in tasks:
                fecha = t.created_at.strftime("%d/%m %H:%M") if t.created_at else "?"
                lines.append(f"- [{t.status}] {t.user_intent[:80]} ({t.domain}, {fecha})")

            return "\n".join(lines)
    except Exception as e:
        logger.debug("Error cargando tareas recientes: %s", e)
        return ""
