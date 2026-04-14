"""Rutas Purchase Orders — thin controller para pedidos de compra."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.erp import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.sales import purchase_order as svc

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/purchase-orders", response_model=list[PurchaseOrderResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_purchase_orders(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_purchase_orders(db, current_user.tenant_id)


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
    data = payload.model_dump(exclude={"lines"})
    lines_data = [l.model_dump() for l in payload.lines]
    return await svc.create_purchase_order(db, current_user.tenant_id, data, lines_data)


@router.patch("/purchase-orders/{order_id}", response_model=PurchaseOrderResponse, tags=["erp"])
@limiter.limit("30/minute")
async def update_purchase_order(
    request: Request,
    order_id: UUID,
    payload: PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_purchase_order(
            db, current_user.tenant_id, order_id, payload.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/purchase-orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
@limiter.limit("30/minute")
async def delete_purchase_order(
    request: Request,
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_purchase_order(db, current_user.tenant_id, order_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
