"""Rutas Sales Orders — thin controller para pedidos de venta."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.erp import (
    SalesOrderCreate,
    SalesOrderResponse,
    SalesOrderUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.sales import order_labels
from app.services.sales import sales_order as svc

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/orders", response_model=list[SalesOrderResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_sales_orders(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_sales_orders(db, current_user.tenant_id)


@router.post("/orders", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED, tags=["erp"])
@limiter.limit("30/minute")
async def create_sales_order(
    request: Request,
    payload: SalesOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude={"lines"})
    lines_data = [line.model_dump() for line in payload.lines]
    return await svc.create_sales_order(db, current_user.tenant_id, data, lines_data)


@router.get("/orders/{order_id}/labels/pdf", tags=["erp"])
@limiter.limit("20/minute")
async def order_labels_pdf(
    request: Request,
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """PDF de etiquetas de prenda del pedido (una por prenda, con código de barras)."""
    try:
        pdf = await order_labels.generate_order_labels_pdf(db, current_user.tenant_id, order_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="etiquetas-pedido.pdf"'},
    )


@router.patch("/orders/{order_id}", response_model=SalesOrderResponse, tags=["erp"])
@limiter.limit("30/minute")
async def update_sales_order(
    request: Request,
    order_id: UUID,
    payload: SalesOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_sales_order(
            db, current_user.tenant_id, order_id, payload.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
@limiter.limit("30/minute")
async def delete_sales_order(
    request: Request,
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_sales_order(db, current_user.tenant_id, order_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
