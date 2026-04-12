"""Banking business logic — raises plain Python exceptions, never HTTPException."""

import random
import uuid
from datetime import date, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import BankTransaction, Invoice
from app.services.event_bus import emit_event
from app.services.state_machine import can_transition


async def get_summary(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Financial summary derived from local invoices."""
    query = select(Invoice).where(Invoice.tenant_id == tenant_id)
    result = await db.execute(query)
    invoices = result.scalars().all()

    ingresos = sum(float(inv.amount_total) for inv in invoices if inv.invoice_type == "issued")
    gastos = sum(float(inv.amount_total) for inv in invoices if inv.invoice_type == "received")

    neto = ingresos - gastos
    margen = round((neto / ingresos) * 100) if ingresos > 0 else 0

    if not invoices:
        return {"ingresos": 0, "gastos": 0, "neto": 0, "margen": 0, "is_demo": False}

    return {
        "ingresos": ingresos,
        "gastos": gastos,
        "neto": neto,
        "margen": margen,
        "is_demo": False,
    }


async def list_transactions(db: AsyncSession, tenant_id: uuid.UUID) -> list:
    """Return all bank transactions for the tenant, newest first."""
    query = (
        select(BankTransaction)
        .where(BankTransaction.tenant_id == tenant_id)
        .order_by(desc(BankTransaction.date))
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def sync_transactions(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> dict:
    """Generate demo bank transactions simulating a PSD2 sync."""
    descriptions = [
        "Recibo Luz Gesternova",
        "Abono Cliente STRIPE",
        "Cuota Seguridad Social",
        "Transferencia recibida F. Perez",
        "Pago Suministros",
    ]
    today = date.today()

    balance = 14500.00
    for i in range(5):
        day_offset = random.randint(0, 15)
        amount = random.uniform(-500, 1500)
        balance += amount
        tx = BankTransaction(
            tenant_id=tenant_id,
            date=today - timedelta(days=day_offset),
            description=random.choice(descriptions),
            amount=round(amount, 2),
            balance=round(balance, 2),
            status="unreconciled",
        )
        db.add(tx)

    await db.commit()
    await emit_event(db, tenant_id, user_id, "banking_synced", {"count": 5})
    return {"message": "Sincronizado correctamente", "status": "ok"}


async def reconcile_transaction(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    tx_id: uuid.UUID,
    invoice_id_str: str,
) -> dict:
    """Reconcile a bank transaction against an invoice."""
    result = await db.execute(
        select(BankTransaction).where(
            BankTransaction.id == tx_id, BankTransaction.tenant_id == tenant_id
        )
    )
    tx = result.scalars().first()
    if not tx:
        raise LookupError("Transaccion no encontrada")

    result_inv = await db.execute(
        select(Invoice).where(
            Invoice.id == uuid.UUID(invoice_id_str), Invoice.tenant_id == tenant_id
        )
    )
    invoice = result_inv.scalars().first()
    if not invoice:
        raise LookupError("Factura no encontrada")

    tx.invoice_id = invoice.id
    tx.status = "reconciled"

    if can_transition("Invoice", invoice.status, "paid"):
        invoice.status = "paid"
    elif invoice.status == "paid":
        pass  # Already paid — idempotent
    else:
        raise ValueError(
            f"No se puede marcar como pagada una factura en estado '{invoice.status}'. "
            f"Emitela primero antes de conciliarla."
        )

    await db.commit()
    await emit_event(
        db,
        tenant_id,
        user_id,
        "invoice_paid",
        {"invoice_number": invoice.invoice_number, "tx_id": str(tx.id)},
    )
    return {"message": "Conciliado correctamente", "status": "ok"}


def get_analytics() -> dict:
    """Return pre-processed cashflow data and AI insights for the Home Page."""
    cashflow_data = [
        {"month": "Sep", "ingresos": 14200, "gastos": 8500},
        {"month": "Oct", "ingresos": 18500, "gastos": 9200},
        {"month": "Nov", "ingresos": 16100, "gastos": 10500},
        {"month": "Dic", "ingresos": 21000, "gastos": 12100},
        {"month": "Ene", "ingresos": 19400, "gastos": 11000},
        {"month": "Feb", "ingresos": 22300, "gastos": 10200},
    ]

    ai_insights = [
        {
            "id": "1",
            "type": "success",
            "title": "Crecimiento sostenido detectado",
            "message": "Los ingresos del Q1 muestran un incremento del 18% frente al mes anterior, impulsado por nuevos clientes de software.",
            "action_text": "Ver informes",
            "action_url": "/banca",
        },
        {
            "id": "2",
            "type": "warning",
            "title": "3 facturas a punto de vencer",
            "message": "Tienes 3 facturas emitidas por un valor total de 4.250\u20ac que vencen esta semana y no estan conciliadas.",
            "action_text": "Revisar facturas",
            "action_url": "/ventas/facturas",
        },
        {
            "id": "3",
            "type": "info",
            "title": "Eficiencia en gastos",
            "message": "En comparacion con tu sector, tus gastos recurrentes (servicios/cloud) estan un 5% optimizados. Buen trabajo!",
            "action_text": "Analizar costes",
            "action_url": "/tesoreria/pagos-y-cobros",
        },
    ]

    return {"cashflow": cashflow_data, "insights": ai_insights}
