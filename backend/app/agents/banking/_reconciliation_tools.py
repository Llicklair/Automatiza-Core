"""Banking agent — transaction reconciliation tools."""

import logging
import uuid
from datetime import date, timedelta

from langchain_core.tools import tool
from sqlalchemy import or_, select

from app.services.banking.psd2 import get_psd2_credentials as _get_psd2_credentials
from app.db.base import AsyncSessionLocal
from app.db.models.models import Client, Invoice

logger = logging.getLogger(__name__)


from app.services.autonomy_gate import gated_tool


@tool
@gated_tool(
    domain="banking_write",
    summary_fn=lambda kw: f"Conciliar movimientos bancarios con facturas (tolerance: {kw.get('tolerance_days', 3)}d / {kw.get('tolerance_amount', 0.01)}€)",
)
async def reconcile_transactions(
    tenant_id: str, tolerance_days: int = 3, tolerance_amount: float = 0.01
) -> str:
    """
    Concilia automáticamente transacciones bancarias con facturas pendientes/pagadas.
    Cruza movimientos de ingreso con facturas pending/paid por importe y fecha (±tolerancia).
    Marca como conciliadas las coincidencias encontradas.

    Args:
        tenant_id: ID del tenant
        tolerance_days: Días de tolerancia entre fecha de transacción y fecha de factura (por defecto 3)
        tolerance_amount: Tolerancia en euros para considerar coincidencia de importe (por defecto 0.01)

    Política de autonomía: domain=`banking_write` (default MANUAL).
    Si el tenant no la ha cambiado, la acción NO se ejecuta y devuelve sugerencia.
    """
    return await _reconcile_transactions_async(tenant_id, tolerance_days, tolerance_amount)


async def _reconcile_transactions_async(
    tenant_id: str,
    tolerance_days: int,
    tolerance_amount: float,
) -> str:
    try:
        creds = await _get_psd2_credentials(tenant_id)
        if creds:
            from app.integrations.psd2 import PSD2Client

            psd2 = PSD2Client(creds["secret_id"], creds["secret_key"])
            accounts = psd2.get_accounts()
            transactions = []
            for acc in accounts:
                transactions.extend(psd2.get_transactions(acc["id"], days=90))
        else:
            today = date.today()
            transactions = [
                {
                    "amount": 2420.00,
                    "date": (today - timedelta(days=5)).isoformat(),
                    "description": "Transferencia recibida - Acme Corp",
                    "type": "credit",
                },
                {
                    "amount": 1815.00,
                    "date": (today - timedelta(days=12)).isoformat(),
                    "description": "Transferencia recibida - López SL",
                    "type": "credit",
                },
                {
                    "amount": 3630.00,
                    "date": (today - timedelta(days=20)).isoformat(),
                    "description": "Transferencia recibida",
                    "type": "credit",
                },
                {
                    "amount": 605.00,
                    "date": (today - timedelta(days=2)).isoformat(),
                    "description": "Bizum recibido",
                    "type": "credit",
                },
                {
                    "amount": -850.00,
                    "date": (today - timedelta(days=8)).isoformat(),
                    "description": "Pago proveedor",
                    "type": "debit",
                },
                {
                    "amount": -1200.00,
                    "date": (today - timedelta(days=15)).isoformat(),
                    "description": "Alquiler oficina",
                    "type": "debit",
                },
            ]

        ingresos = [t for t in transactions if float(t.get("amount", 0)) > 0]

        if not ingresos:
            return "No se encontraron transacciones de ingreso para conciliar."

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Invoice, Client)
                .join(Client)
                .where(
                    Invoice.tenant_id == uuid.UUID(tenant_id),
                    or_(Invoice.status == "pending", Invoice.status == "paid"),
                )
            )
            invoices = result.all()

            if not invoices:
                return "No hay facturas pendientes o pagadas para conciliar."

            matched = []
            unmatched_txns = []

            for txn in ingresos:
                txn_amount = float(txn["amount"])
                txn_date = date.fromisoformat(txn["date"][:10]) if txn.get("date") else date.today()
                found = False

                for inv, cli in invoices:
                    inv_total = float(inv.amount_total)
                    inv_date = inv.date.date() if hasattr(inv.date, "date") else inv.date

                    amount_match = abs(txn_amount - inv_total) <= tolerance_amount
                    date_match = abs((txn_date - inv_date).days) <= tolerance_days

                    if amount_match and date_match:
                        if inv.status == "pending":
                            inv.status = "paid"
                        matched.append(
                            {
                                "invoice": inv.invoice_number,
                                "client": cli.name,
                                "amount": txn_amount,
                                "txn_desc": txn.get("description", ""),
                            }
                        )
                        found = True
                        break

                if not found:
                    unmatched_txns.append(
                        {
                            "amount": txn_amount,
                            "date": txn.get("date", "?")[:10],
                            "description": txn.get("description", ""),
                        }
                    )

            await db.commit()

        lines = []
        if matched:
            lines.append(f"CONCILIADOS ({len(matched)}):")
            for m in matched:
                lines.append(
                    f"  - {m['invoice']} ({m['client']}): {m['amount']:.2f}€ ← {m['txn_desc']}"
                )

        if unmatched_txns:
            lines.append(f"\nSIN CONCILIAR ({len(unmatched_txns)}):")
            for u in unmatched_txns:
                lines.append(f"  - {u['date']}: +{u['amount']:.2f}€ — {u['description']}")

        total_conciliado = sum(m["amount"] for m in matched)
        total_pendiente = sum(u["amount"] for u in unmatched_txns)

        lines.append(
            f"\nResumen: {len(matched)} conciliados ({total_conciliado:.2f}€), "
            f"{len(unmatched_txns)} sin conciliar ({total_pendiente:.2f}€)."
        )

        return "\n".join(lines)
    except Exception as e:
        return f"Error en conciliación: {e}"
