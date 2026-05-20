"""Banking business logic — raises plain Python exceptions, never HTTPException."""

import random
import uuid
from datetime import date, timedelta

from sqlalchemy import desc, extract, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.models import BankTransaction, Invoice
from app.services.analytics import DEMO_TX_PREFIX
from app.services.event_bus import emit_event
from app.services.state_machine import can_transition


def _real_tx_filter():
    """SQLAlchemy filter that excludes demo bank transactions ([DEMO] prefix)."""
    return not_(BankTransaction.description.like(f"{DEMO_TX_PREFIX}%"))


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
    """Genera movimientos DEMO simulando PSD2 (Plaid/Nordigen no integrado).

    Cada transacción se prefija con `[DEMO]` para que las analíticas reales
    puedan filtrarlas y no contaminar las métricas del tenant.
    """
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
            description=f"{DEMO_TX_PREFIX} {random.choice(descriptions)}",
            amount=round(amount, 2),
            balance=round(balance, 2),
            status="unreconciled",
        )
        db.add(tx)

    await db.commit()
    await emit_event(db, tenant_id, user_id, "banking_synced", {"count": 5, "demo": True})
    return {
        "message": "Movimientos demo generados (PSD2 no configurado)",
        "status": "ok",
        "is_demo": True,
        "count": 5,
    }


async def purge_demo_transactions(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Borra todas las transacciones marcadas como demo en el tenant. Devuelve nº borradas."""
    from sqlalchemy import delete

    res = await db.execute(
        delete(BankTransaction).where(
            BankTransaction.tenant_id == tenant_id,
            BankTransaction.description.like(f"{DEMO_TX_PREFIX}%"),
        )
    )
    await db.commit()
    return int(res.rowcount or 0)


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


async def ignore_transaction(
    db: AsyncSession, tenant_id: uuid.UUID, tx_id: uuid.UUID
) -> dict:
    """Mark a bank transaction as ignored (no matching invoice)."""
    result = await db.execute(
        select(BankTransaction).where(BankTransaction.id == tx_id, BankTransaction.tenant_id == tenant_id)
    )
    tx = result.scalars().first()
    if not tx:
        raise LookupError("Transacción no encontrada")
    tx.status = "ignored"
    await db.commit()
    return {"message": "Transacción ignorada", "status": "ok"}


async def unreconcile_transaction(
    db: AsyncSession, tenant_id: uuid.UUID, tx_id: uuid.UUID
) -> dict:
    """Undo a reconciliation: revert tx to unreconciled and invoice to sent."""
    result = await db.execute(
        select(BankTransaction).where(BankTransaction.id == tx_id, BankTransaction.tenant_id == tenant_id)
    )
    tx = result.scalars().first()
    if not tx:
        raise LookupError("Transacción no encontrada")
    if tx.invoice_id:
        inv_res = await db.execute(select(Invoice).where(Invoice.id == tx.invoice_id))
        invoice = inv_res.scalars().first()
        if invoice and invoice.status == "paid":
            invoice.status = "sent"
    tx.status = "unreconciled"
    tx.invoice_id = None
    tx.journal_entry_id = None
    await db.commit()
    return {"message": "Conciliación deshecha", "status": "ok"}


def _score_match(tx, inv, tx_amount: float) -> int:
    """Puntúa un candidato de conciliación (0-100).

    Reglas:
      - Importe exacto (±0.02€): +50  (base; sin esto no es candidato)
      - Fecha factura dentro de ventana razonable: +30 si <=15 días, +15 si <=45 días
      - Nombre cliente aparece en el concepto bancario: +30 (gran señal)
      - Número factura aparece en el concepto: +20
    """
    score = 50  # filtro previo garantiza importe exacto
    desc = (tx.description or "").lower()

    if inv.date and tx.date:
        days = abs((tx.date - inv.date).days)
        if days <= 15:
            score += 30
        elif days <= 45:
            score += 15

    if inv.client and inv.client.name:
        client_name = inv.client.name.lower().strip()
        if client_name and (
            client_name in desc
            or any(tok for tok in client_name.split() if len(tok) >= 4 and tok in desc)
        ):
            score += 30

    if inv.invoice_number:
        inv_num = str(inv.invoice_number).lower()
        if inv_num and inv_num in desc:
            score += 20

    return min(score, 100)


def _candidates_for(tx, invoices, used_ids: set[str]) -> list:
    """Devuelve invoices candidatos rankeados (importe coincide + ranking por score)."""
    tx_amount = abs(float(tx.amount))
    cands = []
    for inv in invoices:
        if str(inv.id) in used_ids:
            continue
        if abs(abs(float(inv.amount_total)) - tx_amount) > 0.02:
            continue
        cands.append((inv, _score_match(tx, inv, tx_amount)))
    cands.sort(key=lambda x: -x[1])
    return cands


async def get_reconciliation_suggestions(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[dict]:
    """Sugerencias de conciliación rankeadas por score (importe + fecha + cliente + nº factura)."""
    tx_res = await db.execute(
        select(BankTransaction)
        .where(BankTransaction.tenant_id == tenant_id, BankTransaction.status == "unreconciled")
        .order_by(desc(BankTransaction.date))
    )
    txs = tx_res.scalars().all()

    inv_res = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.client))
        .where(Invoice.tenant_id == tenant_id, Invoice.status.in_(["sent", "draft"]))
    )
    invoices = list(inv_res.scalars().all())

    out = []
    for tx in txs:
        ranked = _candidates_for(tx, invoices, used_ids=set())
        matched = [
            {
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "amount_total": float(inv.amount_total),
                "client_name": inv.client.name if inv.client else None,
                "status": inv.status,
                "date": inv.date.isoformat() if inv.date else None,
                "score": score,
            }
            for inv, score in ranked
        ]
        out.append({
            "tx": {
                "id": str(tx.id),
                "date": tx.date.isoformat(),
                "description": tx.description,
                "amount": float(tx.amount),
            },
            "suggestions": matched,
        })
    return out


async def auto_reconcile(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> dict:
    """Auto-concilia movimientos con candidato claramente ganador.

    Casa cuando:
      - hay un solo candidato por importe, o
      - el top tiene score >= 80 y el segundo está al menos 30 puntos por debajo
        (ganador claro: importe exacto + fecha próxima + cliente/factura en concepto)
    """
    tx_res = await db.execute(
        select(BankTransaction).where(
            BankTransaction.tenant_id == tenant_id,
            BankTransaction.status == "unreconciled",
        )
    )
    txs = tx_res.scalars().all()

    inv_res = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.client))
        .where(Invoice.tenant_id == tenant_id, Invoice.status.in_(["sent", "draft"]))
    )
    invoices = list(inv_res.scalars().all())

    matched_count = 0
    used_ids: set[str] = set()

    for tx in txs:
        ranked = _candidates_for(tx, invoices, used_ids)
        if not ranked:
            continue

        winner = None
        if len(ranked) == 1:
            winner = ranked[0][0]
        else:
            top_inv, top_score = ranked[0]
            _, second_score = ranked[1]
            if top_score >= 80 and (top_score - second_score) >= 30:
                winner = top_inv

        if winner is not None:
            tx.invoice_id = winner.id
            tx.status = "reconciled"
            if can_transition("Invoice", winner.status, "paid"):
                winner.status = "paid"
            used_ids.add(str(winner.id))
            matched_count += 1

    if matched_count > 0:
        await db.commit()
        await emit_event(db, tenant_id, user_id, "banking_auto_reconciled", {"count": matched_count})

    return {"matched": matched_count, "total": len(txs)}


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
