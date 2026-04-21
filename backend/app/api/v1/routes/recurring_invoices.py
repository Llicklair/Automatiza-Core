"""Rutas para facturas recurrentes — thin controller."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.erp import (
    InvoiceResponse,
    RecurringInvoiceCreate,
    RecurringInvoiceResponse,
    RecurringInvoiceUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.billing import recurring as svc

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/recurring-invoices", response_model=list[RecurringInvoiceResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_recurring_invoices(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_recurring(current_user.tenant_id, db)


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
    return await svc.create_recurring(payload, current_user.tenant_id, db)


@router.patch("/recurring-invoices/{rec_id}", response_model=RecurringInvoiceResponse, tags=["erp"])
@limiter.limit("30/minute")
async def update_recurring_invoice(
    request: Request,
    rec_id: UUID,
    payload: RecurringInvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = await svc.update_recurring(rec_id, payload, current_user.tenant_id, db)
    if not rec:
        raise HTTPException(status_code=404, detail="Factura recurrente no encontrada")
    return rec


@router.delete("/recurring-invoices/{rec_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
@limiter.limit("30/minute")
async def delete_recurring_invoice(
    request: Request,
    rec_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await svc.delete_recurring(rec_id, current_user.tenant_id, db):
        raise HTTPException(status_code=404, detail="Factura recurrente no encontrada")


@router.post("/recurring-invoices/{rec_id}/run", response_model=InvoiceResponse, tags=["erp"])
@limiter.limit("30/minute")
async def run_recurring_invoice(
    request: Request,
    rec_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera manualmente una factura a partir de una plantilla recurrente."""
    invoice = await svc.run_recurring(rec_id, current_user.tenant_id, db)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura recurrente no encontrada")
    return invoice
