"""Banking agent — account balance tools."""

import logging

from langchain_core.tools import tool

from app.agents.banking._psd2_helpers import _DEMO_SALDOS, ALERT_THRESHOLDS
from app.services.banking.psd2 import get_psd2_credentials as _get_psd2_credentials

logger = logging.getLogger(__name__)


@tool
async def check_balances(tenant_id: str) -> str:
    """
    Consulta los saldos actuales de las cuentas bancarias vinculadas.
    Si el banco no está conectado (PSD2), muestra datos de demo.

    Args:
        tenant_id: ID del tenant
    """
    return await _check_balances_async(tenant_id)


async def _check_balances_async(tenant_id: str) -> str:
    creds = await _get_psd2_credentials(tenant_id)

    if not creds:
        lines = [f"- {s['nombre']}: {s['saldo']:.2f}€ ({s['iban']})" for s in _DEMO_SALDOS]
        return (
            "⚠️ Banco no conectado — mostrando datos de demo.\n\n"
            "Saldos:\n"
            + "\n".join(lines)
            + "\n\nConecta tu banco desde Integraciones → PSD2 para ver datos reales."
        )

    from app.integrations.psd2 import NordigenClient

    client = NordigenClient(secret_id=creds["secret_id"], secret_key=creds["secret_key"])
    saldos = []
    alertas = []

    try:
        await client._get_access_token()
        for acc_id in creds.get("account_ids", []):
            try:
                details = await client.get_account_details(acc_id)
                balances = await client.get_account_balances(acc_id)
                saldo_disp = next(
                    (b for b in balances if b.get("balanceType") == "interimAvailable"),
                    balances[0] if balances else {},
                )
                importe = float(saldo_disp.get("balanceAmount", {}).get("amount", 0))
                saldos.append(
                    f"- {details.get('name', 'Cuenta')} ({details.get('iban', '')}): {importe:.2f}€"
                )
                if importe < ALERT_THRESHOLDS["saldo_minimo_eur"]:
                    alertas.append(f"⚠️ Saldo bajo: {importe:.2f}€ en {details.get('iban', acc_id)}")
            except Exception as e:
                logger.exception(
                    "[banking] error obteniendo saldos cuenta acc_id=%s tenant=%s",
                    acc_id, getattr(tenant_id, "hex", tenant_id),
                )
                saldos.append(f"- Cuenta {acc_id}: Error ({type(e).__name__}: {e})")
    finally:
        await client.close()

    result = "Saldos bancarios:\n" + "\n".join(saldos)
    if alertas:
        result += "\n\nAlertas:\n" + "\n".join(alertas)
    return result
