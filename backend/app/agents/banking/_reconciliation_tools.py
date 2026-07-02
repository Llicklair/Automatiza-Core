"""Banking agent — transaction reconciliation tool (delega en el servicio)."""

import logging
import uuid

from langchain_core.tools import tool

from app.db.base import AsyncSessionLocal
from app.services.autonomy_gate import gated_tool

logger = logging.getLogger(__name__)


@tool
@gated_tool(
    domain="banking_write",
    summary_fn=lambda kw: "Conciliar automáticamente los movimientos bancarios con sus facturas",
)
async def reconcile_transactions(tenant_id: str, tolerance_days: int = 3, tolerance_amount: float = 0.01) -> str:
    """
    Concilia automáticamente los movimientos bancarios YA IMPORTADOS con las
    facturas, usando el motor ÚNICO del servicio (importe + fecha + cliente + nº
    factura, filtrado por dirección/invoice_type, idempotente, con asiento de
    cobro). Los parámetros de tolerancia se mantienen por compatibilidad.

    Política de autonomía: domain=`banking_write` (default MANUAL). Si el tenant
    no la ha cambiado, la acción NO se ejecuta y devuelve sugerencia.

    Args:
        tenant_id: ID del tenant
        tolerance_days: (compat) la tolerancia la gestiona ahora el scoring del servicio.
        tolerance_amount: (compat) ídem.
    """
    return await _reconcile_transactions_async(tenant_id)


async def _reconcile_transactions_async(tenant_id: str) -> str:
    # Delega en services/banking/service.py::auto_reconcile, el ÚNICO motor de
    # conciliación: opera sobre los movimientos REALES almacenados
    # (BankTransaction), filtra por dirección/invoice_type, es idempotente y
    # genera el asiento de cobro. Antes este tool tenía un SEGUNDO matcher con
    # transacciones bancarias INVENTADAS (hardcoded) que podía marcar facturas
    # reales como pagadas a partir de datos ficticios — eliminado (B7).
    from app.services.banking.service import auto_reconcile

    try:
        async with AsyncSessionLocal() as db:
            res = await auto_reconcile(db, uuid.UUID(tenant_id), None)
    except Exception as e:
        return f"Error en conciliación: {e}"

    return (
        f"Conciliación automática completada: {res['matched']} de {res['total']} "
        f"movimiento(s) sin conciliar se han casado con su factura (importe + fecha "
        f"+ cliente). Los no conciliados quedan en 'Pagos y cobros' para revisión manual."
    )
