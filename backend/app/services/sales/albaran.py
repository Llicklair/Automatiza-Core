"""Business logic for albaranes (delivery notes)."""

from datetime import date as date_type
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.billing import DeliveryNote, DeliveryNoteLine
from app.db.models.models import Client, Tenant

VALID_STATUSES = ("draft", "confirmed", "delivered")


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


async def list_albaranes(tenant_id: UUID, db: AsyncSession) -> list:
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.tenant_id == tenant_id)
        .options(selectinload(DeliveryNote.lines))
        .order_by(desc(DeliveryNote.created_at))
    )
    return list(result.scalars().all())


async def create_albaran(
    tenant_id: UUID,
    client_id: Optional[UUID],
    entry_date: Optional[date_type],
    notes: Optional[str],
    lines: list,
    db: AsyncSession,
) -> DeliveryNote:
    albaran_number = await _next_albaran_number(tenant_id, db)
    resolved_date = entry_date or date_type.today()

    amount_base = Decimal("0")
    tax_amount = Decimal("0")
    for line in lines:
        base = Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
        tax = base * Decimal(str(line.tax_percentage)) / Decimal("100")
        amount_base += base
        tax_amount += tax
    amount_total = amount_base + tax_amount

    note = DeliveryNote(
        tenant_id=tenant_id,
        client_id=client_id,
        albaran_number=albaran_number,
        date=resolved_date,
        notes=notes,
        amount_base=amount_base,
        tax_amount=tax_amount,
        amount_total=amount_total,
    )
    db.add(note)
    await db.flush()

    for line in lines:
        base = Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
        total = base + base * Decimal(str(line.tax_percentage)) / Decimal("100")
        db.add(
            DeliveryNoteLine(
                albaran_id=note.id,
                product_id=line.product_id,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_percentage=line.tax_percentage,
                total=total,
            )
        )

    await db.commit()
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.id == note.id)
        .options(selectinload(DeliveryNote.lines))
    )
    return result.scalar_one()


async def get_albaran(albaran_id: UUID, tenant_id: UUID, db: AsyncSession) -> DeliveryNote:
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.id == albaran_id, DeliveryNote.tenant_id == tenant_id)
        .options(selectinload(DeliveryNote.lines))
    )
    note = result.scalar_one_or_none()
    if not note:
        raise LookupError("Albaran no encontrado")
    return note


async def update_albaran_status(
    albaran_id: UUID, tenant_id: UUID, new_status: str, db: AsyncSession
) -> DeliveryNote:
    if new_status not in VALID_STATUSES:
        raise ValueError("Estado no valido")
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.id == albaran_id, DeliveryNote.tenant_id == tenant_id)
        .options(selectinload(DeliveryNote.lines))
    )
    note = result.scalar_one_or_none()
    if not note:
        raise LookupError("Albaran no encontrado")
    note.status = new_status
    await db.commit()
    await db.refresh(note)
    return note


async def delete_albaran(albaran_id: UUID, tenant_id: UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(DeliveryNote).where(
            DeliveryNote.id == albaran_id, DeliveryNote.tenant_id == tenant_id
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise LookupError("Albaran no encontrado")
    await db.delete(note)
    await db.commit()


async def get_albaran_pdf_data(
    albaran_id: UUID, tenant_id: UUID, db: AsyncSession
) -> tuple:
    """Return (albaran_data dict, theme, albaran_number) for PDF generation."""
    note = await get_albaran(albaran_id, tenant_id, db)

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
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()

    # Try to get template theme
    theme = None
    try:
        from app.services.template_service import get_default_theme

        theme = await get_default_theme(tenant_id, "albaran", db)
    except Exception:
        pass

    albaran_data: Dict[str, Any] = {
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

    from app.services.pdf import generate_albaran_pdf

    pdf_bytes = generate_albaran_pdf(albaran_data, theme)
    return pdf_bytes, note.albaran_number
