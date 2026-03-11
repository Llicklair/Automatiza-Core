import logging
from datetime import UTC
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.sales import QuoteCreate, QuoteResponse, QuoteUpdate
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Quote, QuoteLine, User

router = APIRouter()

@router.post("/", response_model=QuoteResponse, status_code=201)
async def create_quote(
    quote_in: QuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Calculate totals
    amount_base = 0
    tax_amount = 0
    
    for line in quote_in.lines:
        line_base = line.quantity * line.unit_price
        line_tax = line_base * (line.tax_percentage / 100)
        amount_base += line_base
        tax_amount += line_tax
        
    amount_total = amount_base + tax_amount

    # Create master
    db_quote = Quote(
        tenant_id=current_user.tenant_id,
        client_id=quote_in.client_id,
        quote_number=quote_in.quote_number,
        date=quote_in.date,
        valid_until=quote_in.valid_until,
        amount_base=amount_base,
        tax_amount=tax_amount,
        amount_total=amount_total,
        status=quote_in.status,
        notes=quote_in.notes,
        terms=quote_in.terms,
        opportunity_id=quote_in.opportunity_id
    )
    
    db.add(db_quote)
    await db.flush() # To get the quote id
    
    # Create lines
    for line in quote_in.lines:
        line_base = line.quantity * line.unit_price
        db_line = QuoteLine(
            quote_id=db_quote.id,
            product_id=line.product_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            tax_percentage=line.tax_percentage,
            total_line=line_base
        )
        db.add(db_line)
        
    await db.commit()
    await db.refresh(db_quote)
    
    # Needs to manually load relations for response
    result = await db.execute(
        select(Quote)
        .options(selectinload(Quote.lines), selectinload(Quote.client))
        .where(Quote.id == db_quote.id)
    )
    return result.scalar_one()

@router.get("/", response_model=list[QuoteResponse])
async def list_quotes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    query = (
        select(Quote)
        .where(Quote.tenant_id == current_user.tenant_id)
        .options(selectinload(Quote.lines), selectinload(Quote.client))
        .order_by(Quote.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Quote)
        .where(Quote.id == quote_id, Quote.tenant_id == current_user.tenant_id)
        .options(selectinload(Quote.lines), selectinload(Quote.client))
    )
    result = await db.execute(query)
    quote = result.scalar_one_or_none()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
        
    return quote
    
@router.patch("/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: UUID,
    quote_update: QuoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Quote)
        .where(Quote.id == quote_id, Quote.tenant_id == current_user.tenant_id)
        .options(selectinload(Quote.lines), selectinload(Quote.client))
    )
    result = await db.execute(query)
    quote = result.scalar_one_or_none()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    update_data = quote_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quote, field, value)
        
    await db.commit()
    await db.refresh(quote)
    
    return quote


@router.post("/{quote_id}/convert-to-invoice")
async def convert_quote_to_invoice(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Convierte un presupuesto en una factura real.
    1. Crea una Invoice con las mismas líneas del presupuesto.
    2. Crea los InvoiceLine correspondientes.
    3. Marca el presupuesto como 'accepted'.
    4. Emite el evento 'invoice_created' para activar automatizaciones.
    Devuelve el ID de la factura creada.
    """
    from datetime import datetime

    from sqlalchemy import func

    from app.db.models.models import Invoice, InvoiceLine

    # Cargar el presupuesto con sus líneas
    result = await db.execute(
        select(Quote)
        .options(selectinload(Quote.lines), selectinload(Quote.client))
        .where(Quote.id == quote_id, Quote.tenant_id == current_user.tenant_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    if quote.status == "accepted":
        raise HTTPException(status_code=400, detail="Este presupuesto ya fue convertido en factura")

    # Generar número correlativo
    invoices_res = await db.execute(
        select(func.count(Invoice.id)).where(Invoice.tenant_id == current_user.tenant_id)
    )
    invoice_count = (invoices_res.scalar() or 0) + 1
    now = datetime.now(UTC)
    invoice_number = f"FAC-{now.year}-{invoice_count:04d}"

    # Crear la factura
    new_invoice = Invoice(
        tenant_id=current_user.tenant_id,
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

    # Copiar líneas del presupuesto
    for ql in (quote.lines or []):
        line_base = float(ql.quantity or 1) * float(ql.unit_price or 0)
        line_tax  = line_base * (float(ql.tax_percentage or 21) / 100)
        inv_line = InvoiceLine(
            invoice_id=new_invoice.id,
            product_id=ql.product_id,
            description=ql.description,
            quantity=float(ql.quantity or 1),
            unit_price=float(ql.unit_price or 0),
            tax_percentage=float(ql.tax_percentage or 21),
            discount_percentage=0.0,
            total=line_base + line_tax,
        )
        db.add(inv_line)

    # Marcar presupuesto como aceptado
    quote.status = "accepted"
    await db.commit()

    # Emitir evento
    try:
        from app.services.event_bus import emit_event
        await emit_event(
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
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
        logger.warning("Error al emitir evento invoice_created tras conversión de presupuesto %s: %s", quote_id, e)

    return {
        "invoice_id": str(new_invoice.id),
        "invoice_number": invoice_number,
        "amount_total": float(new_invoice.amount_total),
        "message": f"Presupuesto convertido en factura {invoice_number} correctamente.",
    }


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Quote).where(Quote.id == quote_id, Quote.tenant_id == current_user.tenant_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    await db.delete(quote)
    await db.commit()
