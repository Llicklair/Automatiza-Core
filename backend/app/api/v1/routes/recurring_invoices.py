import datetime as dt_module
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.v1.schemas.erp import (
    InvoiceResponse,
    RecurringInvoiceCreate,
    RecurringInvoiceResponse,
    RecurringInvoiceUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Invoice, InvoiceLine, RecurringInvoice, User
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/recurring-invoices", response_model=list[RecurringInvoiceResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_recurring_invoices(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.tenant_id == current_user.tenant_id)
        .options(joinedload(RecurringInvoice.client))
        .order_by(desc(RecurringInvoice.created_at))
    )
    return result.unique().scalars().all()


@router.post(
    "/recurring-invoices",
    response_model=RecurringInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["erp"],
)
@limiter.limit("30/minute")
async def create_recurring_invoice(
    request: Request,
    payload: RecurringInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = RecurringInvoice(
        tenant_id=current_user.tenant_id,
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


@router.patch("/recurring-invoices/{rec_id}", response_model=RecurringInvoiceResponse, tags=["erp"])
@limiter.limit("30/minute")
async def update_recurring_invoice(
    request: Request,
    rec_id: UUID,
    payload: RecurringInvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(RecurringInvoice).where(
            RecurringInvoice.id == rec_id, RecurringInvoice.tenant_id == current_user.tenant_id
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Factura recurrente no encontrada")
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


@router.delete("/recurring-invoices/{rec_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
@limiter.limit("30/minute")
async def delete_recurring_invoice(
    request: Request,
    rec_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(RecurringInvoice).where(
            RecurringInvoice.id == rec_id, RecurringInvoice.tenant_id == current_user.tenant_id
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Factura recurrente no encontrada")
    await db.delete(rec)
    await db.commit()


@router.post("/recurring-invoices/{rec_id}/run", response_model=InvoiceResponse, tags=["erp"])
@limiter.limit("30/minute")
async def run_recurring_invoice(
    request: Request,
    rec_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera manualmente una factura a partir de una plantilla recurrente."""
    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.id == rec_id, RecurringInvoice.tenant_id == current_user.tenant_id)
        .options(joinedload(RecurringInvoice.client))
    )
    rec = result.unique().scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Factura recurrente no encontrada")

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
        tenant_id=current_user.tenant_id,
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

    # Calcular próxima fecha según intervalo
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
