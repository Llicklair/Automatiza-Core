"""Recepción de mercancía contra pedido de compra.

Al recibir, por cada línea: registra la cantidad recibida (admite recepciones
parciales), da entrada de stock en el almacén indicado (o el por defecto),
crea el lote si se aporta, y actualiza el estado del pedido.

No lanza HTTPException — solo excepciones Python o valores de retorno.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.inventory import Product, StockMovement
from app.db.models.orders import PurchaseOrder
from app.services.inventory import lot_service, stock_service, warehouse_service


async def receive(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    order_id: UUID,
    receipts: list[dict],
    warehouse_id: UUID | None = None,
) -> dict:
    """Procesa la recepción de líneas de un pedido de compra.

    `receipts`: lista de dicts con `line_id` (UUID), `quantity` (float) y,
    opcionalmente, `lot_number` y `expiry_date`.
    """
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order_id, PurchaseOrder.tenant_id == tenant_id)
        .options(selectinload(PurchaseOrder.lines))
    )
    po = result.scalars().first()
    if po is None:
        raise LookupError(f"Pedido de compra {order_id} no encontrado")

    if po.status in ("received", "cancelled"):
        raise ValueError(f"No se puede recibir un pedido en estado '{po.status}'")

    wh = (
        await stock_service.resolve_warehouse(db, tenant_id, warehouse_id)
        if hasattr(stock_service, "resolve_warehouse")
        else (warehouse_id or await warehouse_service.get_default_id(db, tenant_id))
    )

    lines_by_id = {line.id: line for line in po.lines}
    received_summary: list[dict] = []

    for r in receipts:
        line = lines_by_id.get(r["line_id"])
        if line is None:
            continue
        ordered = float(line.quantity or 0)
        already = float(line.received_quantity or 0)
        remaining = ordered - already
        qty = min(float(r.get("quantity") or 0), remaining)
        if qty <= 0:
            continue

        line.received_quantity = already + qty

        if line.product_id:
            prod_res = await db.execute(
                select(Product).where(Product.id == line.product_id, Product.tenant_id == tenant_id)
            )
            product = prod_res.scalars().first()
            if product is not None:
                await stock_service.add_to_warehouse(
                    db, tenant_id=tenant_id, product=product, warehouse_id=wh, qty=int(qty)
                )
                db.add(
                    StockMovement(
                        tenant_id=tenant_id,
                        product_id=product.id,
                        warehouse_id=wh,
                        movement_type="entrada",
                        quantity=int(qty),
                        stock_after=int(product.stock_quantity),
                        unit_cost=line.unit_price,
                        reference=f"PO:{order_id}",
                        notes=f"Recepción pedido {po.order_number or str(po.id)[:8]}",
                    )
                )
                if r.get("lot_number"):
                    await lot_service.add_lot(
                        db,
                        tenant_id=tenant_id,
                        product_id=product.id,
                        lot_number=r["lot_number"],
                        quantity=int(qty),
                        expiry_date=r.get("expiry_date"),
                        cost_price=float(line.unit_price) if line.unit_price is not None else None,
                        warehouse_id=wh,
                    )

        received_summary.append({"line_id": str(line.id), "received": qty})

    all_done = all(float(line.received_quantity or 0) >= float(line.quantity or 0) for line in po.lines)
    any_received = any(float(line.received_quantity or 0) > 0 for line in po.lines)
    if all_done:
        po.status = "received"
    elif any_received:
        po.status = "partially_received"

    await db.commit()
    return {"order_id": str(po.id), "status": po.status, "received": received_summary}
