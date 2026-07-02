"""
Dispatcher de facturación (billing agent).
Invoca el billing agent autónomo (LangGraph) y traduce su resultado
al formato del orquestador.
"""

import logging
from datetime import UTC, datetime, timedelta

from app.agents.orchestrator.dispatchers._outcome import detect_failure
from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.services.orchestration import (
    format_summary,
    messages_already_generated_pdf,
    save_ai_result_as_document,
)

logger = logging.getLogger(__name__)


async def _dispatch_billing(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el billing agent autónomo via LangGraph graph."""
    import uuid

    from app.agents.billing import graph

    tenant_id = state["tenant_id"]
    intent = subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"]))

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

        # Clasificación de la operación. Prioridad: intención del usuario
        # (más fiable). El texto del LLM es fallback porque "Borrador" aparece
        # como estado al listar facturas y disparaba falsos positivos de creación.
        _lower = final_text.lower()
        _intent_lower = (intent or "").lower()
        intent_says_query = any(
            kw in _intent_lower
            for kw in [
                "lista",
                "listar",
                "muestra",
                "muéstra",
                "muestrame",
                "muéstrame",
                "cuáles",
                "cuántas",
                "cuántos",
                "qué facturas",
                "qué albaranes",
                "ver facturas",
                "ver albaranes",
                "buscar",
                "busca ",
            ]
        )
        intent_says_create = any(
            kw in _intent_lower
            for kw in [
                "crea ",
                "crear ",
                "genera factura",
                "emite factura",
                "nueva factura",
                "nuevo albarán",
                "crea albarán",
            ]
        )

        is_approval = "aprobación requerida" in _lower
        is_query = (intent_says_query and not intent_says_create) or any(
            kw in _lower for kw in ["facturas recientes", "total facturado", "no hay facturas"]
        )
        is_creation = (intent_says_create and not intent_says_query) or (
            not is_query
            and any(
                kw in _lower
                for kw in ["factura creada", "borrador creado", "se ha creado la factura", "albarán creado"]
            )
        )

        # Detección ESTRUCTURADA de fallo (señal principal: intent de acción pero
        # ninguna herramienta invocada). strict_not_found=not is_query: en una
        # consulta "no hay facturas" es resultado válido; en una acción "el
        # cliente no existe" es fallo. La aprobación pendiente nunca es fallo.
        is_error, error_text = detect_failure(messages, final_text, intent, strict_not_found=not is_query)
        is_error = is_error and not is_approval
        success = not is_error

        if is_error:
            action = "failed"
        elif is_approval:
            action = "approval_required"
        elif is_creation:
            action = "draft_created"
        elif is_query:
            action = "summary"
        else:
            action = "completed"

        _billing_output = {
            "action": action,
            "response": final_text,
        }

        # No duplicar si el agente ya creó un PDF profesional por su cuenta.
        already_pdf = messages_already_generated_pdf(messages)

        # Guardar resultado como documento visible
        if success and final_text and not already_pdf:
            if is_query:
                await save_ai_result_as_document(
                    tenant_id=tenant_id,
                    task_id=state["task_id"],
                    category="facturas",
                    title=f"Consulta Facturas — {state['task_id'][:8]}",
                    content=final_text,
                )
            elif is_creation:
                await save_ai_result_as_document(
                    tenant_id=tenant_id,
                    task_id=state["task_id"],
                    category="facturas",
                    title=f"Factura IA — {state['task_id'][:8]}",
                    content=final_text,
                )

        # Manejar aprobación humana. La tool create_invoice ya creó un
        # PendingApproval ESTRUCTURADO ({"kind":"create_invoice","params":...})
        # al superar el umbral; lo reutilizamos para no duplicar y para que al
        # aprobar se ejecute la acción real. Fallback a texto solo si no existe.
        if is_approval:
            from sqlalchemy import select

            from app.db.base import AsyncSessionLocal
            from app.db.models.models import PendingApproval

            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(PendingApproval).where(
                        PendingApproval.task_id == uuid.UUID(state["task_id"]),
                        PendingApproval.status == "pending",
                    )
                )
                approval = res.scalars().first()
                if approval is None:
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
                approval_id = str(approval.id)

            return {
                "subtask_id": subtask["id"],
                "agent": "billing",
                "success": True,
                "output": {"action": "approval_required", "approval_id": approval_id},
                "summary": final_text[:200],
                "error": None,
            }

        return {
            "subtask_id": subtask["id"],
            "agent": "billing",
            "success": success,
            "output": _billing_output,
            "summary": format_summary(
                "billing", _billing_output, success, None if success else (error_text or final_text)
            ),
            "error": None if success else (error_text or final_text),
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
