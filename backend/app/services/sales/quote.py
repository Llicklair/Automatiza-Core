"""Quote service — all business logic for quotes (presupuestos)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.models import Invoice, InvoiceLine, Quote, QuoteLine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _quote_query_with_rels():
    return select(Quote).options(selectinload(Quote.lines), selectinload(Quote.client))


async def _get_quote_or_raise(db: AsyncSession, quote_id: UUID, tenant_id: UUID) -> Quote:
    result = await db.execute(
        _quote_query_with_rels().where(Quote.id == quote_id, Quote.tenant_id == tenant_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise LookupError("Quote not found")
    return quote


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_quote(db: AsyncSession, tenant_id: UUID, data: dict) -> Quote:
    lines_data = data.pop("lines", [])

    amount_base = 0.0
    tax_amount = 0.0
    for ln in lines_data:
        line_base = ln["quantity"] * ln["unit_price"]
        line_tax = line_base * (ln["tax_percentage"] / 100)
        amount_base += line_base
        tax_amount += line_tax

    # Remove totals from data because we pass them explicitly below
    data.pop("amount_base", None)
    data.pop("tax_amount", None)
    data.pop("amount_total", None)

    db_quote = Quote(
        tenant_id=tenant_id,
        amount_base=amount_base,
        tax_amount=tax_amount,
        amount_total=amount_base + tax_amount,
        **data,
    )
    db.add(db_quote)
    await db.flush()

    for ln in lines_data:
        line_base = ln["quantity"] * ln["unit_price"]
        db.add(
            QuoteLine(
                quote_id=db_quote.id,
                product_id=ln.get("product_id"),
                description=ln.get("description"),
                quantity=ln["quantity"],
                unit_price=ln["unit_price"],
                tax_percentage=ln["tax_percentage"],
                total_line=line_base,
            )
        )

    await db.commit()

    result = await db.execute(_quote_query_with_rels().where(Quote.id == db_quote.id))
    return result.scalar_one()


async def list_quotes(
    db: AsyncSession, tenant_id: UUID, *, skip: int = 0, limit: int = 100
) -> list[Quote]:
    result = await db.execute(
        _quote_query_with_rels()
        .where(Quote.tenant_id == tenant_id)
        .order_by(Quote.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_quote(db: AsyncSession, quote_id: UUID, tenant_id: UUID) -> Quote:
    return await _get_quote_or_raise(db, quote_id, tenant_id)


async def update_quote(
    db: AsyncSession,
    quote_id: UUID,
    tenant_id: UUID,
    update_data: dict,
) -> Quote:
    quote = await _get_quote_or_raise(db, quote_id, tenant_id)
    for field, value in update_data.items():
        setattr(quote, field, value)
    await db.commit()
    # Reload with relationships so Pydantic can serialize client/lines
    result = await db.execute(
        _quote_query_with_rels().where(Quote.id == quote_id, Quote.tenant_id == tenant_id)
    )
    return result.scalar_one()


async def delete_quote(db: AsyncSession, quote_id: UUID, tenant_id: UUID) -> None:
    result = await db.execute(
        select(Quote).where(Quote.id == quote_id, Quote.tenant_id == tenant_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise LookupError("Quote not found")
    await db.delete(quote)
    await db.commit()


# ---------------------------------------------------------------------------
# Convert quote -> invoice
# ---------------------------------------------------------------------------


async def convert_to_invoice(
    db: AsyncSession,
    quote_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
) -> dict:
    quote = await _get_quote_or_raise(db, quote_id, tenant_id)

    if quote.status == "accepted":
        raise ValueError("Este presupuesto ya fue convertido en factura")

    # Correlative number
    count_res = await db.execute(
        select(func.count(Invoice.id)).where(Invoice.tenant_id == tenant_id)
    )
    invoice_count = (count_res.scalar() or 0) + 1
    now = datetime.now(UTC)
    invoice_number = f"FAC-{now.year}-{invoice_count:04d}"

    new_invoice = Invoice(
        tenant_id=tenant_id,
        client_id=quote.client_id,
        invoice_number=invoice_number,
        date=now,
        amount_base=float(quote.amount_base or 0),
        tax_amount=float(quote.tax_amount or 0),
        amount_total=float(quote.amount_total or 0),
        notes=quote.notes,
        status="draft",
        invoice_type="issued",
    )
    db.add(new_invoice)
    await db.flush()

    for ql in quote.lines or []:
        line_base = float(ql.quantity or 1) * float(ql.unit_price or 0)
        line_tax = line_base * (float(ql.tax_percentage or 21) / 100)
        db.add(
            InvoiceLine(
                invoice_id=new_invoice.id,
                product_id=ql.product_id,
                description=ql.description,
                quantity=float(ql.quantity or 1),
                unit_price=float(ql.unit_price or 0),
                tax_percentage=float(ql.tax_percentage or 21),
                discount_percentage=0.0,
                total=line_base + line_tax,
            )
        )

    quote.status = "accepted"
    await db.commit()

    # Emit event (best-effort)
    try:
        from app.services.event_bus import emit_event

        await emit_event(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            event_name="invoice_created",
            context={
                "invoice_id": str(new_invoice.id),
                "invoice_number": invoice_number,
                "amount_total": float(new_invoice.amount_total),
                "source": "quote_conversion",
                "quote_id": str(quote_id),
                "client_name": quote.client.name if quote.client else None,
            },
        )
    except Exception as e:
        logger.warning(
            "Error al emitir evento invoice_created tras conversion de presupuesto %s: %s",
            quote_id,
            e,
        )

    return {
        "invoice_id": str(new_invoice.id),
        "invoice_number": invoice_number,
        "amount_total": float(new_invoice.amount_total),
        "message": f"Presupuesto convertido en factura {invoice_number} correctamente.",
    }
