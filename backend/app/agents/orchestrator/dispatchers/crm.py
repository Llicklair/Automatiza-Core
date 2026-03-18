"""
Dispatcher de CRM / ventas.
"""
import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary
from app.agents.orchestrator.helpers import _save_ai_result_as_document

logger = logging.getLogger(__name__)


async def _dispatch_crm(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de ventas/CRM — modo determinista:
    1. Crea una oportunidad de venta directamente en la BD.
    2. Guarda el resultado como documento en el Escáner.
    """
    import asyncio
    import uuid

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Client, Opportunity

    tenant_id = state["tenant_id"]
    intent = subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"]))

    action_taken = "Asistencia CRM completada."
    success = True

    try:
        async with AsyncSessionLocal() as db:
            # Buscar cualquier cliente del tenant
            client_result = await db.execute(
                select(Client)
                .where(Client.tenant_id == uuid.UUID(tenant_id))
                .order_by(Client.created_at.desc())
                .limit(1)
            )
            client = client_result.scalars().first()

            if client:
                # Verificar si ya tiene una oportunidad activa
                opp_result = await db.execute(
                    select(Opportunity).where(
                        Opportunity.tenant_id == uuid.UUID(tenant_id),
                        Opportunity.client_id == client.id,
                        Opportunity.stage.not_in(["won", "lost"])
                    ).limit(1)
                )
                existing_opp = opp_result.scalars().first()

                if existing_opp:
                    # Avanzar el estado del lead existente
                    old_stage = existing_opp.stage
                    stage_map = {"new": "qualified", "qualified": "proposal", "proposal": "won"}
                    new_stage = stage_map.get(old_stage, "qualified")
                    existing_opp.stage = new_stage
                    await db.commit()
                    action_taken = (
                        f"Lead del cliente {client.name} avanzado de '{old_stage}' a '{new_stage}' "
                        f"en el embudo de ventas. ID: {existing_opp.id}"
                    )
                else:
                    # Crear nueva oportunidad
                    new_opp = Opportunity(
                        tenant_id=uuid.UUID(tenant_id),
                        client_id=client.id,
                        title=f"Oportunidad IA — {client.name}",
                        expected_value=5000.0,
                        stage="new"
                    )
                    db.add(new_opp)
                    await db.commit()
                    await db.refresh(new_opp)
                    action_taken = (
                        f"Nueva oportunidad de venta creada para {client.name} "
                        f"en fase 'new' por 5.000€. ID: {new_opp.id}"
                    )
            else:
                action_taken = "No hay clientes registrados en el CRM aún."
    except Exception as e:
        success = False
        action_taken = f"Error en CRM: {str(e)}"

    # Guardar resultado como documento visible en el Escáner
    await _save_ai_result_as_document(
            tenant_id=tenant_id,
            task_id=state["task_id"],
            category="crm",
            title=f"Informe CRM — {state['user_intent'][:60]}",
            content=action_taken
        )

    _crm_output = {"action": action_taken}
    return {
        "subtask_id": subtask["id"],
        "agent": "crm",
        "success": success,
        "output": _crm_output,
        "summary": _format_summary("crm", _crm_output, success, None if success else action_taken),
        "error": None if success else action_taken,
    }
