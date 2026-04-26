"""Banking business logic — raises plain Python exceptions, never HTTPException."""

import random
import uuid
from datetime import date, timedelta

from sqlalchemy import desc, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import BankTransaction, Invoice
from app.services.event_bus import emit_event
from app.services.state_machine import can_transition


async def get_summary(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Financial summary derived from invoices in the last 30 days."""
    since = date.today() - timedelta(days=30)
    query = select(Invoice).where(
        Invoice.tenant_id == tenant_id,
        Invoice.date >= since,
    )
    result = await db.execute(query)
    invoices = result.scalars().all()

    ingresos = sum(float(inv.amount_total) for inv in invoices if inv.invoice_type == "issued")
    gastos = sum(float(inv.amount_total) for inv in invoices if inv.invoice_type == "received")

    neto = ingresos - gastos
    margen = round((neto / ingresos) * 100, 1) if ingresos > 0 else 0

    if not invoices:
        return {"ingresos": 0, "gastos": 0, "neto": 0, "margen": 0, "is_demo": False}

    return {
        "ingresos": round(ingresos, 2),
        "gastos": round(gastos, 2),
        "neto": round(neto, 2),
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


async def sync_transactions(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict:
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

    try:
        from app.services.billing.auto_accounting import create_invoice_payment_entry

        entry = await create_invoice_payment_entry(db, tenant_id, invoice)
        if entry:
            tx.journal_entry_id = entry.id
    except Exception as acc_err:
        import logging

        logging.getLogger(__name__).warning("Asiento de cobro no generado: %s", acc_err)

    await db.commit()
    await emit_event(
        db,
        tenant_id,
        user_id,
        "invoice_paid",
        {"invoice_number": invoice.invoice_number, "tx_id": str(tx.id)},
    )
    return {"message": "Conciliado correctamente", "status": "ok"}


async def get_analytics(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Return real cashflow data and dynamic insights for the Home Page."""
    today = date.today()
    month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                   "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    cashflow_data = []
    for i in range(5, -1, -1):
        m_date = today.replace(day=1) - timedelta(days=i * 28)
        y, m = m_date.year, m_date.month

        issued_q = select(func.coalesce(func.sum(Invoice.amount_total), 0)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "issued",
            extract("year", Invoice.date) == y,
            extract("month", Invoice.date) == m,
        )
        received_q = select(func.coalesce(func.sum(Invoice.amount_total), 0)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "received",
            extract("year", Invoice.date) == y,
            extract("month", Invoice.date) == m,
        )
        ingresos = float((await db.execute(issued_q)).scalar())
        gastos = float((await db.execute(received_q)).scalar())
        cashflow_data.append({
            "month": month_names[m - 1],
            "ingresos": round(ingresos, 2),
            "gastos": round(gastos, 2),
        })

    total_ingresos = sum(c["ingresos"] for c in cashflow_data)
    total_gastos = sum(c["gastos"] for c in cashflow_data)
    neto = total_ingresos - total_gastos

    pending_q = select(func.count(), func.coalesce(func.sum(Invoice.amount_total), 0)).where(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_type == "issued",
        Invoice.status.in_(["sent", "draft"]),
        Invoice.due_date <= today + timedelta(days=7),
    )
    pending_res = (await db.execute(pending_q)).one()
    pending_count = pending_res[0]
    pending_amount = float(pending_res[1])

    ai_insights = []
    if total_ingresos > 0 and len(cashflow_data) >= 2:
        prev = cashflow_data[-2]["ingresos"]
        curr = cashflow_data[-1]["ingresos"]
        if prev > 0:
            pct = round(((curr - prev) / prev) * 100, 1)
            if pct > 0:
                ai_insights.append({
                    "id": "1", "type": "success",
                    "title": "Crecimiento detectado",
                    "message": f"Los ingresos de {cashflow_data[-1]['month']} crecieron un {pct}% respecto al mes anterior.",
                    "action_text": "Ver informes", "action_url": "/banca",
                })
            elif pct < -5:
                ai_insights.append({
                    "id": "1", "type": "warning",
                    "title": "Descenso de ingresos",
                    "message": f"Los ingresos de {cashflow_data[-1]['month']} bajaron un {abs(pct)}% respecto al mes anterior.",
                    "action_text": "Ver informes", "action_url": "/banca",
                })

    if pending_count > 0:
        ai_insights.append({
            "id": "2", "type": "warning",
            "title": f"{pending_count} facturas próximas a vencer",
            "message": f"Tienes {pending_count} facturas emitidas por {pending_amount:,.2f}€ que vencen esta semana.",
            "action_text": "Revisar facturas", "action_url": "/ventas/facturas",
        })

    if total_gastos > 0:
        margen = round((neto / total_ingresos) * 100, 1) if total_ingresos > 0 else 0
        ai_insights.append({
            "id": "3", "type": "info" if margen > 20 else "warning",
            "title": f"Margen del periodo: {margen}%",
            "message": f"Ingresos: {total_ingresos:,.2f}€ | Gastos: {total_gastos:,.2f}€ | Beneficio: {neto:,.2f}€ en los últimos 6 meses.",
            "action_text": "Analizar costes", "action_url": "/analitica",
        })

    if not ai_insights:
        ai_insights.append({
            "id": "1", "type": "info",
            "title": "Sin datos suficientes",
            "message": "Crea facturas emitidas y recibidas para ver insights automáticos aquí.",
            "action_text": "Crear factura", "action_url": "/ventas/facturas",
        })

    return {"cashflow": cashflow_data, "insights": ai_insights}
