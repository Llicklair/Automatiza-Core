"""
Dispatcher para agentes de dominio personalizado (domain='custom').
Usa el system_prompt del propio agente como contexto LLM y guarda
el resultado en su carpeta de documentación.
"""

import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary

logger = logging.getLogger(__name__)


async def _dispatch_custom(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Ejecuta un agente de dominio personalizado usando su system_prompt."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from sqlalchemy import select

    from app.core.llm_factory import get_llm_for_tenant
    from app.db.base import AsyncSessionLocal
    from app.db.models.ai_employees import AIEmployee

    tenant_id = state["tenant_id"]
    intent = subtask.get("params", {}).get(
        "intent", state.get("current_intent", state["user_intent"])
    )

    # Obtener datos del agente desde metadata de la tarea
    metadata = state.get("additional_metadata") or {}
    employee_id = metadata.get("addressed_employee_id")

    employee_name = "Agente IA"
    system_prompt = (
        "Eres un asistente profesional de empresa. Ejecutas las tareas asignadas de forma "
        "proactiva y profesional. Comunicas siempre en español, con tono profesional y directo."
    )
    doc_folder = None

    if employee_id:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(AIEmployee).where(AIEmployee.id == employee_id))
                emp = result.scalar_one_or_none()
                if emp:
                    employee_name = emp.name
                    system_prompt = emp.system_prompt or system_prompt
                    doc_folder = emp.doc_folder
        except Exception as e:
            logger.warning("No se pudo cargar el empleado %s: %s", employee_id, e)

    try:
        async with AsyncSessionLocal() as db:
            llm = await get_llm_for_tenant(tenant_id, db, temperature=0.4)

        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=intent),
            ]
        )
        answer = response.content.strip()

        # Guardar en la carpeta de documentación del agente si tiene
        if doc_folder and answer:
            try:
                await _save_to_agent_folder(
                    tenant_id=tenant_id,
                    task_id=state.get("task_id"),
                    agent_name=employee_name,
                    doc_folder=doc_folder,
                    intent=intent,
                    content=answer,
                )
            except Exception as e:
                logger.warning("Error guardando en carpeta del agente: %s", e)

        output = {"action": "completed", "response": answer}
        return {
            "subtask_id": subtask["id"],
            "agent": employee_name,
            "success": True,
            "output": output,
            "summary": _format_summary(employee_name, output, True, None),
            "error": None,
        }

    except Exception as e:
        logger.exception("Error en dispatcher custom (agente: %s)", employee_name)
        return {
            "subtask_id": subtask["id"],
            "agent": employee_name,
            "success": False,
            "output": {"action": "failed", "error": str(e)},
            "summary": f"Error en {employee_name}: {e}",
            "error": str(e),
        }


async def _save_to_agent_folder(
    tenant_id: str,
    task_id: str,
    agent_name: str,
    doc_folder: str,
    intent: str,
    content: str,
) -> None:
    """Persiste el resultado del agente como documento en su carpeta."""

    # Guardar usando la infraestructura de documentos RAG si está disponible
    try:
        from app.agents.orchestrator.helpers import _save_ai_result_as_document

        await _save_ai_result_as_document(
            tenant_id=tenant_id,
            task_id=task_id,
            category=doc_folder,
            title=f"{agent_name} — {intent[:60]}",
            content=content,
        )
    except Exception as e:
        logger.warning("_save_ai_result_as_document no disponible: %s", e)
