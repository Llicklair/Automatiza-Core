"""Product & stock-movement business logic (no HTTP concerns)."""

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Product, StockMovement


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


async def create_product(db: AsyncSession, tenant_id: UUID, data: dict) -> Product:
    product = Product(tenant_id=tenant_id, **data)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update_product(
    db: AsyncSession, tenant_id: UUID, product_id: UUID, data: dict
) -> Product:
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise LookupError("Producto no encontrado")
    for key, value in data.items():
        setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, tenant_id: UUID, product_id: UUID) -> None:
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise LookupError("Producto no encontrado")
    await db.delete(product)
    await db.commit()


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


async def create_stock_movement(
    db: AsyncSession, tenant_id: UUID, product_id: UUID, data: dict
) -> StockMovement:
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise LookupError("Producto no encontrado")

    movement_type = data["movement_type"]
    quantity = data["quantity"]

    if movement_type == "entrada":
        new_stock = int(product.stock_quantity) + abs(quantity)
    elif movement_type == "salida":
        new_stock = int(product.stock_quantity) - abs(quantity)
        if new_stock < 0:
            raise ValueError("Stock insuficiente")
    else:  # ajuste
        new_stock = quantity

    product.stock_quantity = new_stock

    movement = StockMovement(
        tenant_id=tenant_id,
        product_id=product_id,
        movement_type=movement_type,
        quantity=quantity,
        stock_after=new_stock,
        reference=data.get("reference"),
        notes=data.get("notes"),
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)
    return movement
