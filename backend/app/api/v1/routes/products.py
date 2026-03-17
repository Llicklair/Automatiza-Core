import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.erp import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    StockMovementCreate,
    StockMovementResponse,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Product, StockMovement, User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/products", response_model=list[ProductResponse], tags=["erp"])
async def list_products(
    skip: int = 0,
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Product)
        .where(Product.tenant_id == current_user.tenant_id)
        .order_by(desc(Product.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/products/{product_id}", response_model=ProductResponse, tags=["erp"])
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == current_user.tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == current_user.tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    await db.delete(product)
    await db.commit()


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, tags=["erp"])
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_product = Product(
        tenant_id=current_user.tenant_id,
        **payload.model_dump()
    )
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return new_product


# ─── Stock / Inventario ──────────────────────────────────────────────────────


@router.get("/products/{product_id}/stock-movements", response_model=list[StockMovementResponse], tags=["inventory"])
async def list_stock_movements(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(StockMovement)
        .where(StockMovement.product_id == product_id, StockMovement.tenant_id == current_user.tenant_id)
        .order_by(desc(StockMovement.created_at))
        .limit(100)
    )
    return result.scalars().all()


@router.post("/products/{product_id}/stock-movements", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED, tags=["inventory"])
async def create_stock_movement(
    product_id: UUID,
    payload: StockMovementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == current_user.tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Calcular nuevo stock según tipo de movimiento
    if payload.movement_type == "entrada":
        new_stock = int(product.stock_quantity) + abs(payload.quantity)
    elif payload.movement_type == "salida":
        new_stock = int(product.stock_quantity) - abs(payload.quantity)
        if new_stock < 0:
            raise HTTPException(status_code=400, detail="Stock insuficiente")
    else:  # ajuste
        new_stock = payload.quantity

    product.stock_quantity = new_stock

    movement = StockMovement(
        tenant_id=current_user.tenant_id,
        product_id=product_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        stock_after=new_stock,
        reference=payload.reference,
        notes=payload.notes,
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)
    return movement
