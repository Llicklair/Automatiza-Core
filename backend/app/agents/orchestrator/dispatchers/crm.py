"""
Dispatcher de CRM / ventas.
Invoca el CRM agent autónomo (LangGraph) y traduce su resultado
al formato del orquestador.
"""

import logging

from app.agents.orchestrator.helpers import _save_ai_result_as_document
from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary

logger = logging.getLogger(__name__)


async def _dispatch_crm(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente CRM autónomo via LangGraph graph."""
    from app.agents.crm import graph

    tenant_id = state["tenant_id"]
    intent = subtask.get("params", {}).get(
        "intent", state.get("current_intent", state["user_intent"])
    )

    try:
        result_state = await graph.ainvoke(
            {
                "tenant_id": tenant_id,
                "task_id": state.get("task_id"),
                "user_id": state.get("user_id"),
                "user_intent": intent,
                "current_intent": intent,
                "messages": [],
                "agent_results": [],
                "status": "running",
            }
        )

        messages = result_state.get("messages", [])

        final_text = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
                final_text = msg.content
                break

        is_error = final_text.lower().startswith("error")
        success = not is_error

        _crm_output = {
            "action": "completed" if success else "failed",
            "response": final_text,
        }

        if success and final_text:
            await _save_ai_result_as_document(
                tenant_id=tenant_id,
                task_id=state["task_id"],
                category="crm",
                title=f"Informe CRM — {state['user_intent'][:60]}",
                content=final_text,
            )

        return {
            "subtask_id": subtask["id"],
            "agent": "crm",
            "success": success,
            "output": _crm_output,
            "summary": _format_summary(
                "crm", _crm_output, success, None if success else final_text
            ),
            "error": None if success else final_text,
        }

    except Exception as e:
        logger.exception("Error en CRM agent graph")
        return {
            "subtask_id": subtask["id"],
            "agent": "crm",
            "success": False,
            "output": {"action": "failed", "error": str(e)},
            "summary": f"Error en agente CRM: {e}",
            "error": str(e),
        }
