"""Service logic for recurring invoices: CRUD + invoice generation.

Extracted from api/v1/routes/recurring_invoices.py.
"""

import datetime as dt_module
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.models import Invoice, InvoiceLine, RecurringInvoice


async def list_recurring(tenant_id: UUID, db: AsyncSession) -> list:
    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.tenant_id == tenant_id)
        .options(joinedload(RecurringInvoice.client))
        .order_by(desc(RecurringInvoice.created_at))
    )
    return list(result.unique().scalars().all())


async def create_recurring(payload, tenant_id: UUID, db: AsyncSession) -> RecurringInvoice:
    rec = RecurringInvoice(
        tenant_id=tenant_id,
        client_id=payload.client_id,
        name=payload.name,
        interval_type=payload.interval_type,
        next_run_date=payload.next_run_date,
        notes=payload.notes,
        terms=payload.terms,
        lines_json=[line.model_dump() for line in payload.lines],
    )
    db.add(rec)
    await db.commit()
    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.id == rec.id)
        .options(joinedload(RecurringInvoice.client))
    )
    return result.unique().scalar_one()


async def update_recurring(
    rec_id: UUID,
    payload,
    tenant_id: UUID,
    db: AsyncSession,
) -> RecurringInvoice | None:
    """Returns updated record or None if not found."""
    result = await db.execute(
        select(RecurringInvoice).where(
            RecurringInvoice.id == rec_id,
            RecurringInvoice.tenant_id == tenant_id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        return None

    data = payload.model_dump(exclude_unset=True)
    if "lines" in data:
        data["lines_json"] = data.pop("lines")
    for field, value in data.items():
        setattr(rec, field, value)
    await db.commit()

    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.id == rec_id)
        .options(joinedload(RecurringInvoice.client))
    )
    return result.unique().scalar_one()


async def delete_recurring(rec_id: UUID, tenant_id: UUID, db: AsyncSession) -> bool:
    """Returns False if not found."""
    result = await db.execute(
        select(RecurringInvoice).where(
            RecurringInvoice.id == rec_id,
            RecurringInvoice.tenant_id == tenant_id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        return False
    await db.delete(rec)
    await db.commit()
    return True


async def run_recurring(rec_id: UUID, tenant_id: UUID, db: AsyncSession) -> Invoice | None:
    """Generates an invoice from a recurring template. Returns None if not found."""
    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.id == rec_id, RecurringInvoice.tenant_id == tenant_id)
        .options(joinedload(RecurringInvoice.client))
    )
    rec = result.unique().scalar_one_or_none()
    if not rec:
        return None

    now = dt_module.datetime.now(dt_module.timezone.utc)
    invoice_number = f"REC-{now.strftime('%Y%m%d%H%M%S')}"

    amount_base = 0.0
    tax_amount = 0.0
    for line in rec.lines_json or []:
        base = float(line.get("quantity", 1)) * float(line.get("unit_price", 0))
        tax = base * (float(line.get("tax_percentage", 21)) / 100)
        amount_base += base
        tax_amount += tax

    invoice = Invoice(
        tenant_id=tenant_id,
        client_id=rec.client_id,
        invoice_number=invoice_number,
        date=now,
        status="draft",
        invoice_type="issued",
        notes=rec.notes,
        terms=rec.terms,
        amount_base=round(amount_base, 2),
        tax_amount=round(tax_amount, 2),
        amount_total=round(amount_base + tax_amount, 2),
    )
    db.add(invoice)
    await db.flush()

    for line in rec.lines_json or []:
        base = float(line.get("quantity", 1)) * float(line.get("unit_price", 0))
        tax = base * (float(line.get("tax_percentage", 21)) / 100)
        inv_line = InvoiceLine(
            invoice_id=invoice.id,
            description=line.get("description", ""),
            quantity=line.get("quantity", 1),
            unit_price=line.get("unit_price", 0),
            discount_percentage=0,
            tax_percentage=line.get("tax_percentage", 21),
            total=round(base + tax, 2),
        )
        db.add(inv_line)

    # Next run date
    interval_map = {"weekly": 7, "monthly": 30, "quarterly": 90, "yearly": 365}
    days = interval_map.get(rec.interval_type, 30)
    rec.last_run_date = now.date()
    rec.next_run_date = (now + dt_module.timedelta(days=days)).date()

    await db.commit()

    res = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice.id)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
    )
    return res.unique().scalar_one()
