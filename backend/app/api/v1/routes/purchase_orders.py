import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.v1.schemas.erp import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import PurchaseOrder, PurchaseOrderLine, User
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/purchase-orders", response_model=list[PurchaseOrderResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_purchase_orders(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.tenant_id == current_user.tenant_id)
        .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.lines))
        .order_by(desc(PurchaseOrder.created_at))
    )
    return result.unique().scalars().all()


@router.post(
    "/purchase-orders",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["erp"],
)
@limiter.limit("30/minute")
async def create_purchase_order(
    request: Request,
    payload: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order_number = payload.order_number or f"PC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    amount_base = 0.0
    tax_amount = 0.0
    for line in payload.lines:
        base = float(line.quantity) * float(line.unit_price)
        tax = base * (float(line.tax_percentage) / 100)
        amount_base += base
        tax_amount += tax

    order = PurchaseOrder(
        tenant_id=current_user.tenant_id,
        supplier_id=payload.supplier_id,
        order_number=order_number,
        date=payload.date or datetime.now(timezone.utc),
        expected_delivery=payload.expected_delivery,
        notes=payload.notes,
        amount_base=round(amount_base, 2),
        tax_amount=round(tax_amount, 2),
        amount_total=round(amount_base + tax_amount, 2),
    )
    db.add(order)
    await db.flush()

    for line_data in payload.lines:
        base = float(line_data.quantity) * float(line_data.unit_price)
        tax = base * (float(line_data.tax_percentage) / 100)
        line = PurchaseOrderLine(
            order_id=order.id,
            product_id=line_data.product_id,
            description=line_data.description,
            quantity=line_data.quantity,
            unit_price=line_data.unit_price,
            tax_percentage=line_data.tax_percentage,
            total=round(base + tax, 2),
        )
        db.add(line)

    await db.commit()
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order.id)
        .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.lines))
    )
    return result.unique().scalar_one()


@router.patch("/purchase-orders/{order_id}", response_model=PurchaseOrderResponse, tags=["erp"])
@limiter.limit("30/minute")
async def update_purchase_order(
    request: Request,
    order_id: UUID,
    payload: PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == order_id, PurchaseOrder.tenant_id == current_user.tenant_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido de compra no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    await db.commit()
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order_id)
        .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.lines))
    )
    return result.unique().scalar_one()


@router.delete("/purchase-orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
@limiter.limit("30/minute")
async def delete_purchase_order(
    request: Request,
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == order_id, PurchaseOrder.tenant_id == current_user.tenant_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido de compra no encontrado")
    await db.delete(order)
    await db.commit()
