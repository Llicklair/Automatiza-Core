import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.v1.schemas.erp import (
    SalesOrderCreate,
    SalesOrderResponse,
    SalesOrderUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import SalesOrder, SalesOrderLine, User
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/orders", response_model=list[SalesOrderResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_sales_orders(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.tenant_id == current_user.tenant_id)
        .options(
            joinedload(SalesOrder.client),
            joinedload(SalesOrder.lines),
        )
        .order_by(desc(SalesOrder.created_at))
    )
    return result.unique().scalars().all()


@router.post(
    "/orders", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED, tags=["erp"]
)
@limiter.limit("30/minute")
async def create_sales_order(
    request: Request,
    payload: SalesOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order_number = payload.order_number or f"PED-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Calcular totales
    amount_base = 0.0
    tax_amount = 0.0
    for line in payload.lines:
        base = line.quantity * line.unit_price * (1 - line.discount_percentage / 100)
        tax = base * (line.tax_percentage / 100)
        amount_base += base
        tax_amount += tax

    order = SalesOrder(
        tenant_id=current_user.tenant_id,
        client_id=payload.client_id,
        order_number=order_number,
        date=payload.date or datetime.now(timezone.utc),
        expected_delivery=payload.expected_delivery,
        notes=payload.notes,
        quote_id=payload.quote_id,
        amount_base=round(amount_base, 2),
        tax_amount=round(tax_amount, 2),
        amount_total=round(amount_base + tax_amount, 2),
    )
    db.add(order)
    await db.flush()

    for line_data in payload.lines:
        base = line_data.quantity * line_data.unit_price * (1 - line_data.discount_percentage / 100)
        tax = base * (line_data.tax_percentage / 100)
        line = SalesOrderLine(
            order_id=order.id,
            product_id=line_data.product_id,
            description=line_data.description,
            quantity=line_data.quantity,
            unit_price=line_data.unit_price,
            discount_percentage=line_data.discount_percentage,
            tax_percentage=line_data.tax_percentage,
            total=round(base + tax, 2),
        )
        db.add(line)

    await db.commit()
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == order.id)
        .options(joinedload(SalesOrder.client), joinedload(SalesOrder.lines))
    )
    return result.unique().scalar_one()


@router.patch("/orders/{order_id}", response_model=SalesOrderResponse, tags=["erp"])
@limiter.limit("30/minute")
async def update_sales_order(
    request: Request,
    order_id: UUID,
    payload: SalesOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SalesOrder).where(
            SalesOrder.id == order_id, SalesOrder.tenant_id == current_user.tenant_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    await db.commit()
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == order_id)
        .options(joinedload(SalesOrder.client), joinedload(SalesOrder.lines))
    )
    return result.unique().scalar_one()


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
@limiter.limit("30/minute")
async def delete_sales_order(
    request: Request,
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SalesOrder).where(
            SalesOrder.id == order_id, SalesOrder.tenant_id == current_user.tenant_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    await db.delete(order)
    await db.commit()
