from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.models import SalesOrder, SalesOrderLine


async def list_sales_orders(
    db: AsyncSession, tenant_id: UUID
) -> list[SalesOrder]:
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.tenant_id == tenant_id)
        .options(
            joinedload(SalesOrder.client),
            joinedload(SalesOrder.lines),
        )
        .order_by(desc(SalesOrder.created_at))
    )
    return list(result.unique().scalars().all())


async def create_sales_order(
    db: AsyncSession, tenant_id: UUID, data: dict, lines_data: list[dict]
) -> SalesOrder:
    order_number = data.pop("order_number", None) or f"PED-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Calcular totales
    amount_base = 0.0
    tax_amount = 0.0
    for line in lines_data:
        base = line["quantity"] * line["unit_price"] * (1 - line["discount_percentage"] / 100)
        tax = base * (line["tax_percentage"] / 100)
        amount_base += base
        tax_amount += tax

    order = SalesOrder(
        tenant_id=tenant_id,
        order_number=order_number,
        date=data.pop("date", None) or datetime.now(timezone.utc),
        amount_base=round(amount_base, 2),
        tax_amount=round(tax_amount, 2),
        amount_total=round(amount_base + tax_amount, 2),
        **data,
    )
    db.add(order)
    await db.flush()

    for ld in lines_data:
        base = ld["quantity"] * ld["unit_price"] * (1 - ld["discount_percentage"] / 100)
        tax = base * (ld["tax_percentage"] / 100)
        line = SalesOrderLine(
            order_id=order.id,
            product_id=ld.get("product_id"),
            description=ld["description"],
            quantity=ld["quantity"],
            unit_price=ld["unit_price"],
            discount_percentage=ld["discount_percentage"],
            tax_percentage=ld["tax_percentage"],
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


async def update_sales_order(
    db: AsyncSession, tenant_id: UUID, order_id: UUID, data: dict
) -> SalesOrder:
    result = await db.execute(
        select(SalesOrder).where(
            SalesOrder.id == order_id, SalesOrder.tenant_id == tenant_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise LookupError("Pedido no encontrado")
    for field, value in data.items():
        setattr(order, field, value)
    await db.commit()
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == order_id)
        .options(joinedload(SalesOrder.client), joinedload(SalesOrder.lines))
    )
    return result.unique().scalar_one()


async def delete_sales_order(
    db: AsyncSession, tenant_id: UUID, order_id: UUID
) -> None:
    result = await db.execute(
        select(SalesOrder).where(
            SalesOrder.id == order_id, SalesOrder.tenant_id == tenant_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise LookupError("Pedido no encontrado")
    await db.delete(order)
    await db.commit()
