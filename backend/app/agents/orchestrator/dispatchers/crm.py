"""
Dispatcher de CRM / ventas.
Invoca el CRM agent autónomo (LangGraph) y traduce su resultado
al formato del orquestador.
"""

import logging

from app.services.orchestration import (
    format_summary,
    messages_already_generated_pdf,
    save_ai_result_as_document,
)
from app.agents.orchestrator.state import AgentResult, OrchestratorState

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

        # Detección robusta de error: prefix "error" + frases de fallo comunes
        # que el LLM produce cuando una tool no existe / no devuelve datos / pide
        # más info al usuario. Sin esto, respuestas como "Las herramientas del
        # CRM no están disponibles" se clasificaban como success=True.
        _lower = final_text.lower()
        _error_signals = [
            _lower.startswith("error"),
            "no se pudo" in _lower,
            "no fue posible" in _lower,
            "falló" in _lower,
            "fallo al" in _lower,
            "imposible" in _lower,
            "no such tool" in _lower,
            # Solo detectar "no están disponibles" cuando se refiere a las
            # tools/herramientas del agente — no a campos opcionales de datos
            # que el LLM menciona como "tales campos no están disponibles".
            "herramientas" in _lower and "no están disponibles" in _lower,
            "herramientas no disponibles" in _lower,
            "tool no está disponible" in _lower,
            "no se encontró" in _lower,
            "no se ha encontrado" in _lower,
            "necesito el nif" in _lower,
            "podrías proporcionarme" in _lower,
        ]
        agent_status = result_state.get("status", "")
        is_error = any(_error_signals) or agent_status in ("failed", "error")
        success = not is_error

        _crm_output = {
            "action": "completed" if success else "failed",
            "response": final_text,
        }

        if success and final_text and not messages_already_generated_pdf(messages):
            await save_ai_result_as_document(
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
            "summary": format_summary(
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
