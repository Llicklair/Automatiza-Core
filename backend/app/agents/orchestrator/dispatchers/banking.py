"""
Dispatcher bancario (banking agent).
"""
import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary
from app.agents.orchestrator.helpers import (
    _save_ai_result_as_document,
    _save_ai_result_as_csv,
)

logger = logging.getLogger(__name__)


async def _dispatch_banking(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente bancario."""
    import uuid

    from sqlalchemy import select

    from app.agents.banking_agent import run_banking_agent
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantIntegration
    from app.services.encryption import decrypt_credentials

    tenant_id = state["tenant_id"]
    nordigen_id = nordigen_key = None

    # Obtener credenciales de PSD2 si están configuradas
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TenantIntegration).where(
                TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                TenantIntegration.integration_type == "psd2",
                TenantIntegration.is_active.is_(True),
            )
        )
        integration = result.scalars().first()

    if integration:
        try:
            creds = decrypt_credentials(integration.encrypted_credentials)
            nordigen_id = creds.get("secret_id")
            nordigen_key = creds.get("secret_key")
        except Exception as e:
            logger.warning("Error al descifrar credenciales PSD2 para tenant %s: %s", tenant_id, e)

    agent_result = await run_banking_agent(
        user_intent=subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"])),
        tenant_id=tenant_id,
        nordigen_secret_id=nordigen_id,
        nordigen_secret_key=nordigen_key,
        account_ids=["acc_demo_123"],  # Mocked account
    )

    # Guardar resultado como documento si fue exitoso
    if agent_result.success:
        content_parts = []
        if agent_result.resumen_financiero:
            content_parts.append(f"Resumen financiero:\n{agent_result.resumen_financiero}")
        if agent_result.saldos:
            saldos_txt = "\n".join(f"  • {s.get('nombre', 'Cuenta')} ({s.get('iban')}): {s.get('saldo')} {s.get('moneda', 'EUR')}" for s in agent_result.saldos)
            content_parts.append(f"Saldos:\n{saldos_txt}")
        if agent_result.alertas:
            content_parts.append("Alertas:\n" + "\n".join(f"- {a}" for a in agent_result.alertas))
        await _save_ai_result_as_document(
            tenant_id=tenant_id,
            task_id=state["task_id"],
            category="bancos",
            title=f"Informe Bancario IA — {state['user_intent'][:60]}",
            content="\n\n".join(content_parts) if content_parts else "Análisis bancario completado.",
        )
        # Exportar transacciones a CSV para que el agente de Excel pueda procesarlas
        if agent_result.transacciones:
            await _save_ai_result_as_csv(
                tenant_id=tenant_id,
                task_id=state["task_id"],
                category="bancos",
                filename=f"movimientos_bancos_{state['task_id'][:8]}.csv",
                data=agent_result.transacciones
            )

    _banking_output = {
        "action":             agent_result.action,
        "resumen_financiero": agent_result.resumen_financiero,
        "saldos":             agent_result.saldos,
        "transacciones":      agent_result.transacciones,
        "alertas":            agent_result.alertas,
    }
    return {
        "subtask_id": subtask["id"],
        "agent": "banking",
        "success": agent_result.success,
        "output": _banking_output,
        "summary": _format_summary("banking", _banking_output, agent_result.success, agent_result.error),
        "error": agent_result.error,
    }
