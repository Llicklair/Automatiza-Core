import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.erp import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    StockMovementCreate,
    StockMovementResponse,
    StockValuationResponse,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.sales import product as svc

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/products", response_model=list[ProductResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_products(
    request: Request,
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    q: str | None = Query(default=None, description="Búsqueda en nombre, SKU y código de barras"),
    category: str | None = None,
    is_active: bool | None = None,
    status: str | None = Query(default=None, pattern="^(ok|low_stock|out_of_stock)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_products(
        db,
        current_user.tenant_id,
        skip,
        limit,
        q=q,
        category=category,
        is_active=is_active,
        status=status,
    )


@router.get(
    "/products/by-barcode/{code}", response_model=ProductResponse, tags=["inventory"]
)
@limiter.limit("60/minute")
async def get_product_by_barcode(
    request: Request,
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = await svc.get_product_by_barcode(db, current_user.tenant_id, code)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


@router.patch("/products/{product_id}", response_model=ProductResponse, tags=["erp"])
@limiter.limit("30/minute")
async def update_product(
    request: Request,
    product_id: UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_product(
            db, current_user.tenant_id, product_id, payload.model_dump(exclude_none=True)
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
@limiter.limit("30/minute")
async def delete_product(
    request: Request,
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_product(db, current_user.tenant_id, product_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, tags=["erp"]
)
@limiter.limit("30/minute")
async def create_product(
    request: Request,
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.create_product(db, current_user.tenant_id, payload.model_dump())


# ─── Stock / Inventario ──────────────────────────────────────────────────────


@router.get("/stock/valuation", response_model=StockValuationResponse, tags=["inventory"])
@limiter.limit("10/minute")
async def stock_valuation(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_stock_valuation(db, current_user.tenant_id)


@router.get(
    "/products/{product_id}/stock-movements",
    response_model=list[StockMovementResponse],
    tags=["inventory"],
)
@limiter.limit("30/minute")
async def list_stock_movements(
    request: Request,
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_stock_movements(db, current_user.tenant_id, product_id)


@router.post(
    "/products/{product_id}/stock-movements",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["inventory"],
)
@limiter.limit("30/minute")
async def create_stock_movement(
    request: Request,
    product_id: UUID,
    payload: StockMovementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump()
    data["user_id"] = current_user.id
    try:
        return await svc.create_stock_movement(
            db, current_user.tenant_id, product_id, data
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
