"""
Dispatcher de documentos (documents agent).
Invoca el documents agent autónomo (LangGraph) y traduce su resultado
al formato del orquestador.
"""

import logging

from app.agents.orchestrator.helpers import (
    _save_ai_result_as_document,
)
from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary

logger = logging.getLogger(__name__)


async def _dispatch_documents(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de documentos autónomo via LangGraph graph."""
    from app.agents.documents import graph

    tenant_id = state["tenant_id"]
    intent = subtask.get("params", {}).get(
        "intent", state.get("current_intent", state["user_intent"])
    )

    # Enriquecer el intent con el document_id si hay un documento vinculado a la tarea
    enriched_intent = intent
    try:
        import uuid

        from sqlalchemy import select

        from app.db.base import AsyncSessionLocal
        from app.db.models.models import TenantDocument

        async with AsyncSessionLocal() as db:
            doc_result = await db.execute(
                select(TenantDocument).where(TenantDocument.task_id == uuid.UUID(state["task_id"]))
            )
            linked_doc = doc_result.scalars().first()
            if linked_doc:
                enriched_intent = (
                    f"{intent}\n\n[CONTEXTO: El documento vinculado a esta tarea es "
                    f"'{linked_doc.file_name}' con ID: {linked_doc.id}. "
                    f"Usa classify_document con document_id='{linked_doc.id}' para analizarlo.]"
                )
    except Exception:
        logger.debug("Error enriqueciendo intent con documento vinculado", exc_info=True)

    try:
        result_state = await graph.ainvoke(
            {
                "tenant_id": tenant_id,
                "task_id": state.get("task_id"),
                "user_id": state.get("user_id"),
                "user_intent": enriched_intent,
                "current_intent": enriched_intent,
                "messages": [],
                "agent_results": [],
                "status": "running",
            }
        )

        messages = result_state.get("messages", [])

        # Extraer respuesta final
        final_text = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
                final_text = msg.content
                break

        is_error = final_text.lower().startswith("error")
        success = not is_error

        _doc_output = {
            "action": "completed" if success else "failed",
            "response": final_text,
        }

        # Guardar resultado como documento visible
        if success and final_text:
            await _save_ai_result_as_document(
                tenant_id=tenant_id,
                task_id=state["task_id"],
                category="documentos",
                title=f"Análisis Documento — {state['task_id'][:8]}",
                content=final_text,
            )

        return {
            "subtask_id": subtask["id"],
            "agent": "documents",
            "success": success,
            "output": _doc_output,
            "summary": _format_summary(
                "documents", _doc_output, success, None if success else final_text
            ),
            "error": None if success else final_text,
        }

    except Exception as e:
        logger.exception("Error en documents agent graph")
        return {
            "subtask_id": subtask["id"],
            "agent": "documents",
            "success": False,
            "output": {"action": "failed", "error": str(e)},
            "summary": f"Error en agente de documentos: {e}",
            "error": str(e),
        }
