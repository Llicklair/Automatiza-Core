"""
Dispatcher de facturación (billing agent).
Invoca el billing agent autónomo (LangGraph) y traduce su resultado
al formato del orquestador.
"""

import logging
from datetime import UTC, datetime, timedelta

from app.agents.orchestrator.helpers import (
    _messages_already_generated_pdf,
    _save_ai_result_as_document,
)
from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary

logger = logging.getLogger(__name__)


async def _dispatch_billing(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el billing agent autónomo via LangGraph graph."""
    import uuid

    from app.agents.billing import graph

    tenant_id = state["tenant_id"]
    intent = subtask.get("params", {}).get(
        "intent", state.get("current_intent", state["user_intent"])
    )

    try:
        # Ejecutar el grafo autónomo del agente de facturación
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

        # Extraer el resultado final del último mensaje del agente
        messages = result_state.get("messages", [])
        result_state.get("agent_results", [])

        # El último mensaje con contenido de texto es la respuesta final
        final_text = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
                final_text = msg.content
                break

        # Detectar si fue una creación exitosa, consulta, o error
        _lower = final_text.lower()
        is_creation = any(kw in _lower for kw in ["factura creada", "draft", "borrador"])
        is_approval = "aprobación requerida" in _lower
        is_query = any(
            kw in _lower for kw in ["facturas recientes", "total facturado", "no hay facturas"]
        )

        # Detección robusta de error: no solo prefix "error", también frases de fallo comunes
        _error_signals = [
            _lower.startswith("error"),
            "no se pudo" in _lower,
            "no fue posible" in _lower,
            "falló" in _lower,
            "fallo al" in _lower,
            "imposible" in _lower,
            "no existe" in _lower and not is_query,
        ]
        is_error = any(_error_signals) and not is_creation and not is_approval

        # Si el grafo del agente reportó status de error, respetar eso
        agent_status = result_state.get("status", "")
        if agent_status in ("failed", "error"):
            is_error = True

        success = not is_error

        if is_approval:
            action = "approval_required"
        elif is_creation:
            action = "draft_created"
        elif is_query:
            action = "summary"
        else:
            action = "completed" if success else "failed"

        _billing_output = {
            "action": action,
            "response": final_text,
        }

        # No duplicar si el agente ya creó un PDF profesional por su cuenta.
        already_pdf = _messages_already_generated_pdf(messages)

        # Guardar resultado como documento visible
        if success and final_text and not already_pdf:
            if is_query:
                await _save_ai_result_as_document(
                    tenant_id=tenant_id,
                    task_id=state["task_id"],
                    category="facturas",
                    title=f"Consulta Facturas — {state['task_id'][:8]}",
                    content=final_text,
                )
            elif is_creation:
                await _save_ai_result_as_document(
                    tenant_id=tenant_id,
                    task_id=state["task_id"],
                    category="facturas",
                    title=f"Factura IA — {state['task_id'][:8]}",
                    content=final_text,
                )

        # Manejar aprobación humana
        if is_approval:
            from app.db.base import AsyncSessionLocal
            from app.db.models.models import PendingApproval

            async with AsyncSessionLocal() as db:
                approval = PendingApproval(
                    task_id=uuid.UUID(state["task_id"]),
                    tenant_id=uuid.UUID(tenant_id),
                    action_description=final_text[:500],
                    action_payload={"intent": intent, "agent_response": final_text},
                    risk_level="high",
                    expires_at=datetime.now(UTC) + timedelta(hours=2),
                )
                db.add(approval)
                await db.commit()
                await db.refresh(approval)

            return {
                "subtask_id": subtask["id"],
                "agent": "billing",
                "success": True,
                "output": {"action": "approval_required", "approval_id": str(approval.id)},
                "summary": final_text[:200],
                "error": None,
            }

        return {
            "subtask_id": subtask["id"],
            "agent": "billing",
            "success": success,
            "output": _billing_output,
            "summary": _format_summary(
                "billing", _billing_output, success, None if success else final_text
            ),
            "error": None if success else final_text,
        }

    except Exception as e:
        logger.exception("Error en billing agent graph")
        return {
            "subtask_id": subtask["id"],
            "agent": "billing",
            "success": False,
            "output": {"action": "failed", "error": str(e)},
            "summary": f"Error en agente de facturación: {e}",
            "error": str(e),
        }
