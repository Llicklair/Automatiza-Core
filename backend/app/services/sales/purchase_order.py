from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.models import PurchaseOrder, PurchaseOrderLine


async def list_purchase_orders(db: AsyncSession, tenant_id: UUID) -> list[PurchaseOrder]:
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.tenant_id == tenant_id)
        .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.lines))
        .order_by(desc(PurchaseOrder.created_at))
    )
    return list(result.unique().scalars().all())


async def create_purchase_order(
    db: AsyncSession, tenant_id: UUID, data: dict, lines_data: list[dict]
) -> PurchaseOrder:
    order_number = data.pop("order_number", None) or f"PC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    amount_base = 0.0
    tax_amount = 0.0
    for line in lines_data:
        base = float(line["quantity"]) * float(line["unit_price"])
        tax = base * (float(line["tax_percentage"]) / 100)
        amount_base += base
        tax_amount += tax

    order = PurchaseOrder(
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
        base = float(ld["quantity"]) * float(ld["unit_price"])
        tax = base * (float(ld["tax_percentage"]) / 100)
        line = PurchaseOrderLine(
            order_id=order.id,
            product_id=ld.get("product_id"),
            description=ld["description"],
            quantity=ld["quantity"],
            unit_price=ld["unit_price"],
            tax_percentage=ld["tax_percentage"],
            total=round(base + tax, 2),
        )
        db.add(line)

    await db.commit()
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order.id)
        .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.lines))
    )
    return result.unique().scalar_one()


async def update_purchase_order(
    db: AsyncSession, tenant_id: UUID, order_id: UUID, data: dict
) -> PurchaseOrder:
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == order_id, PurchaseOrder.tenant_id == tenant_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise LookupError("Pedido de compra no encontrado")
    for field, value in data.items():
        setattr(order, field, value)
    await db.commit()
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order_id)
        .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.lines))
    )
    return result.unique().scalar_one()


async def delete_purchase_order(db: AsyncSession, tenant_id: UUID, order_id: UUID) -> None:
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == order_id, PurchaseOrder.tenant_id == tenant_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise LookupError("Pedido de compra no encontrado")
    await db.delete(order)
    await db.commit()
