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
from app.api.v1.schemas.lots import LotCreate, LotUpdate
from app.api.v1.schemas.warehouse import StockTransferRequest
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.inventory import lot_service, reorder_service, stock_service
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


@router.get("/products/by-barcode/{code}", response_model=ProductResponse, tags=["inventory"])
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
        return await svc.update_product(db, current_user.tenant_id, product_id, payload.model_dump(exclude_none=True))
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


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, tags=["erp"])
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
        return await svc.create_stock_movement(db, current_user.tenant_id, product_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ─── Lotes (caducidad / FEFO) ─────────────────────────────────────────────────


@router.get("/inventory/expiring-lots", tags=["inventory"])
@limiter.limit("30/minute")
async def list_expiring_lots(
    request: Request,
    days: int = Query(default=7, ge=0, le=365, description="Horizonte de caducidad en días"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lotes (de todo el negocio) que caducan dentro de `days` días o ya caducados."""
    return await lot_service.list_expiring_lots(db, current_user.tenant_id, days)


@router.get("/products/{product_id}/lots", tags=["inventory"])
@limiter.limit("30/minute")
async def list_product_lots(
    request: Request,
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista los lotes con stock de un producto, ordenados por caducidad (FEFO)."""
    try:
        return await lot_service.list_lots(db, current_user.tenant_id, product_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/products/{product_id}/lots",
    status_code=status.HTTP_201_CREATED,
    tags=["inventory"],
)
@limiter.limit("30/minute")
async def create_product_lot(
    request: Request,
    product_id: UUID,
    payload: LotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Da de alta un lote (recepción): crea el lote, suma stock y registra el movimiento."""
    try:
        return await lot_service.create_lot(
            db,
            tenant_id=current_user.tenant_id,
            product_id=product_id,
            lot_number=payload.lot_number,
            quantity=payload.quantity,
            expiry_date=payload.expiry_date,
            cost_price=payload.cost_price,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/products/{product_id}/lots/{lot_id}", tags=["inventory"])
@limiter.limit("30/minute")
async def update_product_lot(
    request: Request,
    product_id: UUID,
    lot_id: UUID,
    payload: LotUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edita metadatos de un lote (número, caducidad, coste). No cambia la cantidad."""
    try:
        return await lot_service.update_lot_metadata(
            db, current_user.tenant_id, lot_id, payload.model_dump(exclude_unset=True)
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/products/{product_id}/stock-by-warehouse", tags=["inventory"])
@limiter.limit("30/minute")
async def stock_by_warehouse(
    request: Request,
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Desglose de stock del producto por almacén (el almacén por defecto se deriva)."""
    try:
        return await stock_service.get_by_warehouse(db, current_user.tenant_id, product_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/inventory/transfer", tags=["inventory"])
@limiter.limit("30/minute")
async def transfer_stock(
    request: Request,
    payload: StockTransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Transfiere stock (y lotes en orden FEFO) entre dos almacenes."""
    try:
        return await stock_service.transfer(
            db,
            tenant_id=current_user.tenant_id,
            product_id=payload.product_id,
            from_warehouse_id=payload.from_warehouse_id,
            to_warehouse_id=payload.to_warehouse_id,
            quantity=payload.quantity,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/inventory/reorder-suggestions", tags=["inventory"])
@limiter.limit("30/minute")
async def reorder_suggestions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Productos en o por debajo de su punto de pedido, con cantidad sugerida."""
    return await reorder_service.suggest_reorders(db, current_user.tenant_id)


@router.post("/inventory/reorder/generate-pos", tags=["inventory"])
@limiter.limit("10/minute")
async def reorder_generate_pos(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera pedidos de compra BORRADOR agrupando las sugerencias por proveedor."""
    return await reorder_service.generate_draft_pos(db, current_user.tenant_id)
