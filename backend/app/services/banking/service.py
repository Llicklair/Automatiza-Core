"""Banking business logic — raises plain Python exceptions, never HTTPException."""

import random
import uuid
from datetime import date, datetime, timedelta

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


class BankSyncNotAvailableError(Exception):
    """El tenant no puede sincronizar: PSD2 sin configurar y demo desactivado."""


async def sync_transactions(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    """Sincroniza movimientos bancarios.

    Sin sync PSD2 real cableado todavía: si `BANKING_DEMO_SYNC` está activo
    genera movimientos prefijados con `[DEMO]` (filtrados de las analíticas);
    si no, lanza BankSyncNotAvailableError — un piloto no debe ver movimientos
    inventados en su contabilidad.
    """
    from app.core.config import settings
    from app.services.banking.psd2 import get_psd2_credentials

    if not settings.BANKING_DEMO_SYNC:
        creds = await get_psd2_credentials(str(tenant_id))
        if creds:
            raise BankSyncNotAvailableError(
                "La sincronización automática PSD2 aún no está disponible. "
                "Importa el extracto bancario (Norma 43) desde Banca."
            )
        raise BankSyncNotAvailableError(
            "PSD2 no configurado. Conecta tu banco en Integraciones "
            "o importa el extracto bancario (Norma 43)."
        )

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


async def _apply_payment_entry(db, tenant_id, tx, invoice) -> None:
    """Genera el asiento de cobro/pago (idempotente) y enlaza tx.journal_entry_id.

    Best-effort: un fallo contable (p.ej. periodo cerrado) no debe abortar la
    conciliación. Compartido por la conciliación manual y la automática para que
    ambas dejen la MISMA huella contable — antes auto_reconcile marcaba la factura
    pagada SIN generar el asiento de cobro (B16).
    """
    try:
        from app.services.billing.auto_accounting import create_invoice_payment_entry

        entry = await create_invoice_payment_entry(db, tenant_id, invoice)
        if entry:
            tx.journal_entry_id = entry.id
    except Exception as acc_err:
        import logging

        logging.getLogger(__name__).warning("Asiento de cobro no generado: %s", acc_err)


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

    await _apply_payment_entry(db, tenant_id, tx, invoice)

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
        inv_res = await db.execute(
            select(Invoice).where(Invoice.id == tx.invoice_id, Invoice.tenant_id == tenant_id)
        )
        invoice = inv_res.scalars().first()
        if invoice and invoice.status == "paid":
            invoice.status = "sent"
    tx.status = "unreconciled"
    tx.invoice_id = None
    tx.journal_entry_id = None
    await db.commit()
    return {"message": "Conciliación deshecha", "status": "ok"}


_LEGAL_SUFFIXES = (" s.l.", " sl", " s.a.", " sa", " s.l.u.", " slu", " sccl", " coop")


def _normalize_client_name(name: str) -> str:
    """Elimina sufijos societarios y caracteres no alfanuméricos para mejorar
    el matching contra el concepto del movimiento bancario."""
    s = (name or "").lower().strip()
    for suf in _LEGAL_SUFFIXES:
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
            break
    return s


def _as_date(value):
    """Normaliza date|datetime a `date`.

    Las fechas de los movimientos bancarios (parseadas del N43) son `date`, mientras
    que las de factura se guardan como `datetime`; restarlas directamente lanza
    TypeError. Coerciona ambas a `date` antes de comparar.
    """
    return value.date() if isinstance(value, datetime) else value


def _explain_match(tx, inv, tx_amount: float) -> tuple[int, list[dict]]:
    """Puntúa un candidato (0-100) y devuelve las razones legibles.

    Cada razón tiene la forma {code, label, points}. El frontend las muestra
    como "Este movimiento = factura X porque ..." (F2.6 explicabilidad).

    Reglas (mismas que antes, ahora desglosadas):
      - Importe exacto (±0.02€): +50  (base; sin esto no es candidato)
      - Fecha factura dentro de ventana razonable: +30 si <=15 días, +15 si <=45 días
      - Nombre cliente aparece en el concepto bancario: +30 (gran señal)
      - Número factura aparece en el concepto: +20
    """
    score = 50
    reasons: list[dict] = [
        {"code": "amount_exact", "label": f"Importe exacto ({tx_amount:.2f} €)", "points": 50}
    ]
    desc = (tx.description or "").lower()

    if inv.date and tx.date:
        days = abs((_as_date(tx.date) - _as_date(inv.date)).days)
        if days <= 15:
            score += 30
            reasons.append(
                {"code": "date_within_15d", "label": f"Fecha próxima ({days} día(s))", "points": 30}
            )
        elif days <= 45:
            score += 15
            reasons.append(
                {"code": "date_within_45d", "label": f"Fecha aceptable ({days} día(s))", "points": 15}
            )

    if inv.client and inv.client.name:
        client_name = _normalize_client_name(inv.client.name)
        if client_name:
            tokens = [tok for tok in client_name.split() if len(tok) >= 4]
            matched_token = next((tok for tok in tokens if tok in desc), None)
            if client_name in desc:
                score += 30
                reasons.append(
                    {"code": "client_name_match", "label": f"Cliente '{inv.client.name}' en el concepto", "points": 30}
                )
            elif matched_token:
                score += 30
                reasons.append(
                    {"code": "client_token_match", "label": f"Cliente reconocido por '{matched_token}' en el concepto", "points": 30}
                )

    if inv.invoice_number:
        inv_num = str(inv.invoice_number).lower()
        if inv_num and inv_num in desc:
            score += 20
            reasons.append(
                {"code": "invoice_number_match", "label": f"Nº factura {inv.invoice_number} en el concepto", "points": 20}
            )

    return min(score, 100), reasons


def _score_match(tx, inv, tx_amount: float) -> int:
    """Compat: mantiene la firma antigua devolviendo sólo el score."""
    score, _ = _explain_match(tx, inv, tx_amount)
    return score


def _candidates_for(tx, invoices, used_ids: set[str]) -> list:
    """Devuelve invoices candidatos con (inv, score, reasons)."""
    tx_raw = float(tx.amount)
    tx_amount = abs(tx_raw)
    # B6 — dirección: un cobro (tx>0) solo casa con facturas EMITIDAS
    # (issued/rectificativa); un pago (tx<0) solo con facturas RECIBIDAS. Antes
    # se casaba por importe absoluto ignorando invoice_type y el signo, así que
    # un cargo podía conciliarse contra una factura emitida (y viceversa).
    want_emitted = tx_raw >= 0
    cands = []
    for inv in invoices:
        if str(inv.id) in used_ids:
            continue
        is_emitted = (inv.invoice_type or "issued") != "received"
        if is_emitted != want_emitted:
            continue
        if abs(abs(float(inv.amount_total)) - tx_amount) > 0.02:
            continue
        score, reasons = _explain_match(tx, inv, tx_amount)
        cands.append((inv, score, reasons))
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
        .limit(200)
    )
    txs = tx_res.scalars().all()
    if not txs:
        return []

    # Pre-filtro en SQL: solo facturas cuyo importe cae en el rango de las txs
    # (±0.02€, el mismo umbral que _candidates_for). Evita el producto
    # cartesiano txs × todas las facturas en memoria.
    amounts = [abs(float(tx.amount)) for tx in txs]
    inv_res = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.client))
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(["pending", "sent", "draft"]),
            func.abs(Invoice.amount_total).between(min(amounts) - 0.02, max(amounts) + 0.02),
        )
    )
    invoices = list(inv_res.scalars().all())

    # F2.6 — descartar pares (tx, invoice) que el usuario ya rechazó antes.
    rejected_pairs = await _load_rejected_pairs(db, tenant_id)

    out = []
    for tx in txs:
        ranked = [
            (inv, score, reasons)
            for inv, score, reasons in _candidates_for(tx, invoices, used_ids=set())
            if (str(tx.id), str(inv.id)) not in rejected_pairs
        ]
        matched = [
            {
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "amount_total": float(inv.amount_total),
                "client_name": inv.client.name if inv.client else None,
                "status": inv.status,
                "date": inv.date.isoformat() if inv.date else None,
                "score": score,
                "reasons": reasons,
            }
            for inv, score, reasons in ranked
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
        .where(Invoice.tenant_id == tenant_id, Invoice.status.in_(["pending", "sent", "draft"]))
    )
    invoices = list(inv_res.scalars().all())

    matched_count = 0
    used_ids: set[str] = set()
    rejected_pairs = await _load_rejected_pairs(db, tenant_id)

    for tx in txs:
        ranked = [
            (inv, score, reasons)
            for inv, score, reasons in _candidates_for(tx, invoices, used_ids)
            if (str(tx.id), str(inv.id)) not in rejected_pairs
        ]
        if not ranked:
            continue

        winner = None
        if len(ranked) == 1:
            winner = ranked[0][0]
        else:
            top_inv, top_score, _ = ranked[0]
            _, second_score, _ = ranked[1]
            if top_score >= 80 and (top_score - second_score) >= 30:
                winner = top_inv

        if winner is not None:
            tx.invoice_id = winner.id
            tx.status = "reconciled"
            if can_transition("Invoice", winner.status, "paid"):
                winner.status = "paid"
            # Mismo asiento de cobro (idempotente) que la conciliación manual:
            # antes auto_reconcile dejaba la contabilidad sin el asiento (B16).
            if winner.status == "paid":
                await _apply_payment_entry(db, tenant_id, tx, winner)
            used_ids.add(str(winner.id))
            matched_count += 1

    if matched_count > 0:
        await db.commit()
        await emit_event(db, tenant_id, user_id, "banking_auto_reconciled", {"count": matched_count})

    return {"matched": matched_count, "total": len(txs)}


# ─── F2.6 — Rechazos persistentes ───────────────────────────────────────


async def _load_rejected_pairs(db: AsyncSession, tenant_id: uuid.UUID) -> set[tuple[str, str]]:
    """Carga el conjunto de (tx_id, invoice_id) que el usuario rechazó.

    Devuelve un set vacío si la tabla aún no está migrada (compat al rodar
    sin la 0034 — degrada con elegancia).
    """
    from app.db.models.reconciliation import ReconciliationRejection

    try:
        res = await db.execute(
            select(
                ReconciliationRejection.transaction_id,
                ReconciliationRejection.invoice_id,
            ).where(ReconciliationRejection.tenant_id == tenant_id)
        )
        return {(str(tx), str(inv)) for tx, inv in res.all()}
    except Exception:
        return set()


async def reject_reconciliation_suggestion(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    transaction_id: uuid.UUID,
    invoice_id: uuid.UUID,
    reason: str | None = None,
) -> dict:
    """Marca un par (tx, invoice) como rechazado por el usuario para que no
    vuelva a sugerirse. Idempotente (upsert por par).
    """
    from app.db.models.reconciliation import ReconciliationRejection

    existing = await db.execute(
        select(ReconciliationRejection).where(
            ReconciliationRejection.tenant_id == tenant_id,
            ReconciliationRejection.transaction_id == transaction_id,
            ReconciliationRejection.invoice_id == invoice_id,
        )
    )
    row = existing.scalar_one_or_none()
    if row is None:
        db.add(
            ReconciliationRejection(
                tenant_id=tenant_id,
                transaction_id=transaction_id,
                invoice_id=invoice_id,
                reason=reason,
            )
        )
        await db.commit()
        return {"rejected": True, "new": True}
    if reason and not row.reason:
        row.reason = reason
        await db.commit()
    return {"rejected": True, "new": False}


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
        Invoice.status.in_(["pending", "sent", "draft"]),
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
