"""Almacenes / tiendas (multi-almacén, capa 1)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.warehouse import WarehouseCreate, WarehouseUpdate
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.inventory import warehouse_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/warehouses", tags=["inventory"])
@limiter.limit("30/minute")
async def list_warehouses(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await warehouse_service.list_warehouses(db, current_user.tenant_id)


@router.post("/warehouses", status_code=status.HTTP_201_CREATED, tags=["inventory"])
@limiter.limit("30/minute")
async def create_warehouse(
    request: Request,
    payload: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await warehouse_service.create_warehouse(db, current_user.tenant_id, payload.model_dump())


@router.patch("/warehouses/{warehouse_id}", tags=["inventory"])
@limiter.limit("30/minute")
async def update_warehouse(
    request: Request,
    warehouse_id: UUID,
    payload: WarehouseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await warehouse_service.update_warehouse(
            db, current_user.tenant_id, warehouse_id, payload.model_dump(exclude_unset=True)
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
