"""Albaranes (delivery notes) API routes."""
from datetime import date as date_type
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.billing import DeliveryNote, DeliveryNoteLine
from app.db.models.models import Client, Tenant, User
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/albaranes", tags=["albaranes"])

# ─── Schemas ──────────────────────────────────────────────────────────────────

class DeliveryNoteLineCreate(BaseModel):
    product_id: Optional[UUID] = None
    description: str
    quantity: float = 1
    unit_price: float = 0
    tax_percentage: float = 21

class DeliveryNoteCreate(BaseModel):
    client_id: Optional[UUID] = None
    client_name: Optional[str] = None
    date: Optional[date_type] = None
    notes: Optional[str] = None
    lines: List[DeliveryNoteLineCreate] = []

class DeliveryNoteStatusUpdate(BaseModel):
    status: str  # draft, confirmed, delivered

class DeliveryNoteLineResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    description: str
    quantity: float
    unit_price: float
    tax_percentage: float
    total: float
    model_config = {"from_attributes": True}

class DeliveryNoteResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    client_id: Optional[UUID] = None
    albaran_number: str
    date: date_type
    status: str
    notes: Optional[str] = None
    amount_base: float
    tax_amount: float
    amount_total: float
    created_at: Optional[str] = None
    lines: List[DeliveryNoteLineResponse] = []
    model_config = {"from_attributes": True}

# ─── Helper ───────────────────────────────────────────────────────────────────

async def _next_albaran_number(tenant_id: UUID, db: AsyncSession) -> str:
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.tenant_id == tenant_id)
        .order_by(desc(DeliveryNote.created_at))
        .limit(1)
    )
    last = result.scalar_one_or_none()
    if last and last.albaran_number:
        try:
            num = int(last.albaran_number.split("-")[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1
    return f"ALB-{num:05d}"

# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("", response_model=List[DeliveryNoteResponse])
@limiter.limit("30/minute")
async def list_albaranes(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.tenant_id == current_user.tenant_id)
        .options(selectinload(DeliveryNote.lines))
        .order_by(desc(DeliveryNote.created_at))
    )
    return result.scalars().all()


@router.post("", response_model=DeliveryNoteResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_albaran(
    request: Request,
    payload: DeliveryNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from decimal import Decimal
    albaran_number = await _next_albaran_number(current_user.tenant_id, db)
    entry_date = payload.date or date_type.today()

    amount_base = Decimal("0")
    tax_amount = Decimal("0")
    for line in payload.lines:
        base = Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
        tax = base * Decimal(str(line.tax_percentage)) / Decimal("100")
        amount_base += base
        tax_amount += tax
    amount_total = amount_base + tax_amount

    note = DeliveryNote(
        tenant_id=current_user.tenant_id,
        client_id=payload.client_id,
        albaran_number=albaran_number,
        date=entry_date,
        notes=payload.notes,
        amount_base=amount_base,
        tax_amount=tax_amount,
        amount_total=amount_total,
    )
    db.add(note)
    await db.flush()

    for line in payload.lines:
        base = Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
        total = base + base * Decimal(str(line.tax_percentage)) / Decimal("100")
        db.add(DeliveryNoteLine(
            albaran_id=note.id,
            product_id=line.product_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            tax_percentage=line.tax_percentage,
            total=total,
        ))

    await db.commit()
    result = await db.execute(
        select(DeliveryNote).where(DeliveryNote.id == note.id).options(selectinload(DeliveryNote.lines))
    )
    return result.scalar_one()


@router.get("/{albaran_id}", response_model=DeliveryNoteResponse)
@limiter.limit("30/minute")
async def get_albaran(
    request: Request,
    albaran_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.id == albaran_id, DeliveryNote.tenant_id == current_user.tenant_id)
        .options(selectinload(DeliveryNote.lines))
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Albarán no encontrado")
    return note


@router.patch("/{albaran_id}/status", response_model=DeliveryNoteResponse)
@limiter.limit("30/minute")
async def update_albaran_status(
    request: Request,
    albaran_id: UUID,
    payload: DeliveryNoteStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.status not in ("draft", "confirmed", "delivered"):
        raise HTTPException(status_code=400, detail="Estado no válido")
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.id == albaran_id, DeliveryNote.tenant_id == current_user.tenant_id)
        .options(selectinload(DeliveryNote.lines))
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Albarán no encontrado")
    note.status = payload.status
    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/{albaran_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_albaran(
    request: Request,
    albaran_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.id == albaran_id, DeliveryNote.tenant_id == current_user.tenant_id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Albarán no encontrado")
    await db.delete(note)
    await db.commit()


@router.get("/{albaran_id}/pdf")
@limiter.limit("30/minute")
async def get_albaran_pdf(
    request: Request,
    albaran_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.id == albaran_id, DeliveryNote.tenant_id == current_user.tenant_id)
        .options(selectinload(DeliveryNote.lines))
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Albarán no encontrado")

    # Resolve client name
    client_name = ""
    client_nif = ""
    if note.client_id:
        client_result = await db.execute(select(Client).where(Client.id == note.client_id))
        client = client_result.scalar_one_or_none()
        if client:
            client_name = client.name or ""
            client_nif = client.nif or ""

    # Resolve tenant info for issuer
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()

    # Try to get template theme
    theme = None
    try:
        from app.api.v1.routes.templates import get_default_theme
        theme = await get_default_theme(current_user.tenant_id, "albaran", db)
    except Exception:
        pass

    albaran_data = {
        "albaran_number": note.albaran_number,
        "date": str(note.date),
        "status": note.status,
        "client_name": client_name,
        "client_nif": client_nif,
        "issuer_name": getattr(tenant, "name", "") if tenant else "",
        "issuer_nif": getattr(tenant, "nif", "") if tenant else "",
        "issuer_address": getattr(tenant, "address", "") if tenant else "",
        "notes": note.notes or "",
        "amount_base": float(note.amount_base),
        "tax_amount": float(note.tax_amount),
        "amount_total": float(note.amount_total),
        "lines": [
            {
                "description": line.description,
                "quantity": float(line.quantity),
                "unit_price": float(line.unit_price),
                "tax_percentage": float(line.tax_percentage),
                "total": float(line.total),
            }
            for line in note.lines
        ],
    }

    from app.services.pdf_albaranes import generate_albaran_pdf
    pdf_bytes = generate_albaran_pdf(albaran_data, theme)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="albaran-{note.albaran_number}.pdf"'},
    )
