"""Sales domain — read-only queries (CQRS-lite).

All functions here are pure SELECT operations with no side-effects.
Write operations live in commands.py.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.billing import DeliveryNote
from app.db.models.models import (
    Client,
    Invoice,
    Product,
    PurchaseOrder,
    Quote,
    SalesOrder,
    StockMovement,
    Tenant,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# client queries
# ---------------------------------------------------------------------------


async def list_clients(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 50,
    client_type: str | None = None,
) -> list[Client]:
    query = select(Client).where(Client.tenant_id == tenant_id)
    if client_type:
        query = query.where(Client.client_type == client_type)
    query = query.order_by(desc(Client.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_client_invoices(
    db: AsyncSession,
    tenant_id: UUID,
    client_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Invoice]:
    client_result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    )
    if not client_result.scalar_one_or_none():
        raise LookupError("Cliente no encontrado")

    query = (
        select(Invoice)
        .options(
            joinedload(Invoice.client),
            joinedload(Invoice.lines),
        )
        .where(
            Invoice.client_id == client_id,
            Invoice.tenant_id == tenant_id,
        )
        .order_by(desc(Invoice.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.unique().scalars().all())


# ---------------------------------------------------------------------------
# product queries
# ---------------------------------------------------------------------------


async def list_products(
    db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 50
) -> list[Product]:
    result = await db.execute(
        select(Product)
        .where(Product.tenant_id == tenant_id)
        .order_by(desc(Product.created_at))
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_stock_movements(
    db: AsyncSession, tenant_id: UUID, product_id: UUID
) -> list[StockMovement]:
    result = await db.execute(
        select(StockMovement)
        .where(
            StockMovement.product_id == product_id,
            StockMovement.tenant_id == tenant_id,
        )
        .order_by(desc(StockMovement.created_at))
        .limit(100)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# quote queries
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


# ---------------------------------------------------------------------------
# albaran queries
# ---------------------------------------------------------------------------


async def list_albaranes(tenant_id: UUID, db: AsyncSession) -> list:
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.tenant_id == tenant_id)
        .options(selectinload(DeliveryNote.lines))
        .order_by(desc(DeliveryNote.created_at))
    )
    return list(result.scalars().all())


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


async def get_albaran_pdf_data(albaran_id: UUID, tenant_id: UUID, db: AsyncSession) -> tuple:
    """Return (pdf_bytes, albaran_number) for PDF generation."""
    from typing import Any, Dict

    note = await get_albaran(albaran_id, tenant_id, db)

    client_name = ""
    client_nif = ""
    if note.client_id:
        client_result = await db.execute(select(Client).where(Client.id == note.client_id))
        client = client_result.scalar_one_or_none()
        if client:
            client_name = client.name or ""
            client_nif = client.nif or ""

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()

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


# ---------------------------------------------------------------------------
# purchase_order queries
# ---------------------------------------------------------------------------


async def list_purchase_orders(db: AsyncSession, tenant_id: UUID) -> list[PurchaseOrder]:
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.tenant_id == tenant_id)
        .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.lines))
        .order_by(desc(PurchaseOrder.created_at))
    )
    return list(result.unique().scalars().all())


# ---------------------------------------------------------------------------
# sales_order queries
# ---------------------------------------------------------------------------


async def list_sales_orders(db: AsyncSession, tenant_id: UUID) -> list[SalesOrder]:
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.tenant_id == tenant_id)
        .options(
            joinedload(SalesOrder.client),
            joinedload(SalesOrder.lines),
        )
        .order_by(desc(SalesOrder.created_at))
    )
    return list(result.unique().scalars().all())
