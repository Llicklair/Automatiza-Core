"""Stock por almacén (multi-almacén, capa 2).

Diseño: el stock del **almacén por defecto se deriva** como
`Product.stock_quantity (total global) − Σ(stock de los demás almacenes)`.
Así, los flujos existentes (ventas, TPV, escáner, movimientos) siguen
actualizando solo el total global y el desglose por almacén se mantiene
coherente sin tocarlos. Solo las **transferencias** escriben filas
`product_stock` de almacenes NO-default.

No lanza HTTPException — solo excepciones Python o valores de retorno.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.inventory import Product, ProductLot, ProductStock, Warehouse

from ._fefo import plan_fefo_deduction


async def decrement_product_stock(db: AsyncSession, product: Product, qty: int) -> None:
    """Decremento ATÓMICO y race-safe de Product.stock_quantity.

    UPDATE condicional `... WHERE stock_quantity >= qty`: dos transacciones
    concurrentes se serializan por el row-lock del UPDATE y la segunda re-evalúa
    el WHERE sobre el valor ya decrementado → nunca queda negativo. Si no hay
    stock suficiente, NO modifica nada y lanza ValueError. Sincroniza el atributo
    en memoria (para `stock_after`). NO commitea (lo controla el caller).
    """
    if qty <= 0:
        return
    res = await db.execute(
        update(Product)
        .where(
            Product.id == product.id,
            Product.tenant_id == product.tenant_id,
            Product.stock_quantity >= qty,
        )
        .values(stock_quantity=Product.stock_quantity - qty)
    )
    await db.refresh(product, ["stock_quantity"])
    if res.rowcount != 1:
        raise ValueError(
            f"Stock insuficiente para '{product.name}' "
            f"(disponible {product.stock_quantity}, solicitado {qty})"
        )


async def _default_warehouse_id(db: AsyncSession, tenant_id: UUID) -> UUID | None:
    res = await db.execute(
        select(Warehouse.id).where(Warehouse.tenant_id == tenant_id, Warehouse.is_default.is_(True)).limit(1)
    )
    return res.scalars().first()


async def _global_stock(db: AsyncSession, tenant_id: UUID, product_id: UUID) -> int:
    res = await db.execute(
        select(Product.stock_quantity).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    val = res.scalars().first()
    if val is None:
        raise LookupError(f"Producto {product_id} no encontrado")
    return int(val)


async def _row(db: AsyncSession, product_id: UUID, warehouse_id: UUID) -> ProductStock | None:
    res = await db.execute(
        select(ProductStock).where(ProductStock.product_id == product_id, ProductStock.warehouse_id == warehouse_id)
    )
    return res.scalars().first()


async def _nondefault_total(db: AsyncSession, tenant_id: UUID, product_id: UUID, default_id: UUID | None) -> int:
    q = select(func.coalesce(func.sum(ProductStock.quantity), 0)).where(
        ProductStock.tenant_id == tenant_id, ProductStock.product_id == product_id
    )
    if default_id is not None:
        q = q.where(ProductStock.warehouse_id != default_id)
    res = await db.execute(q)
    return int(res.scalar() or 0)


async def _set_nondefault(
    db: AsyncSession, *, tenant_id: UUID, product_id: UUID, warehouse_id: UUID, delta: int
) -> None:
    """Suma `delta` al stock de un almacén NO-default (crea fila si no existe)."""
    row = await _row(db, product_id, warehouse_id)
    if row is None:
        db.add(
            ProductStock(
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=max(0, int(delta)),
            )
        )
    else:
        row.quantity = max(0, int(row.quantity) + int(delta))


async def get_by_warehouse(db: AsyncSession, tenant_id: UUID, product_id: UUID) -> list[dict]:
    """Desglose de stock por almacén. El almacén por defecto se calcula como
    total global menos lo asignado a los demás almacenes."""
    global_stock = await _global_stock(db, tenant_id, product_id)
    default_id = await _default_warehouse_id(db, tenant_id)

    wh_res = await db.execute(
        select(Warehouse)
        .where(Warehouse.tenant_id == tenant_id, Warehouse.is_active.is_(True))
        .order_by(Warehouse.is_default.desc(), Warehouse.name.asc())
    )
    warehouses = list(wh_res.scalars().all())

    rows_res = await db.execute(
        select(ProductStock.warehouse_id, ProductStock.quantity).where(
            ProductStock.tenant_id == tenant_id, ProductStock.product_id == product_id
        )
    )
    stored = {wid: int(q) for wid, q in rows_res.all()}
    nondefault_total = sum(q for wid, q in stored.items() if wid != default_id)

    out: list[dict] = []
    for w in warehouses:
        if w.is_default:
            # El default = global − suma de los no-default. Suelo a 0: si los
            # no-default superan el global (desfase), no mostramos stock negativo
            # (carecía de sentido y confundía la lectura) (B19).
            qty = max(0, global_stock - nondefault_total)
        else:
            qty = stored.get(w.id, 0)
        out.append(
            {
                "warehouse_id": str(w.id),
                "warehouse_name": w.name,
                "is_default": bool(w.is_default),
                "quantity": int(qty),
            }
        )
    return out


async def _available_in(
    db: AsyncSession, tenant_id: UUID, product_id: UUID, warehouse_id: UUID, default_id: UUID | None
) -> int:
    if default_id is not None and warehouse_id == default_id:
        global_stock = await _global_stock(db, tenant_id, product_id)
        return global_stock - await _nondefault_total(db, tenant_id, product_id, default_id)
    row = await _row(db, product_id, warehouse_id)
    return int(row.quantity) if row else 0


async def add_to_warehouse(
    db: AsyncSession, *, tenant_id: UUID, product, warehouse_id: UUID, qty: int
) -> None:
    """Entrada de `qty` unidades en un almacén: sube el total global del producto
    y, si el almacén no es el por defecto, su fila `product_stock` (el por
    defecto se deriva). No commitea."""
    product.stock_quantity = int(product.stock_quantity or 0) + int(qty)
    default_id = await _default_warehouse_id(db, tenant_id)
    if default_id is not None and warehouse_id != default_id:
        await _set_nondefault(
            db, tenant_id=tenant_id, product_id=product.id, warehouse_id=warehouse_id, delta=int(qty)
        )


async def transfer(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    product_id: UUID,
    from_warehouse_id: UUID,
    to_warehouse_id: UUID,
    quantity: int,
) -> dict:
    """Transfiere unidades entre almacenes. No cambia el total global; solo
    redistribuye. Mueve también los lotes (FEFO) si los hay en el origen."""
    qty = abs(int(quantity))
    if qty <= 0:
        raise ValueError("La cantidad debe ser mayor que cero")
    if from_warehouse_id == to_warehouse_id:
        raise ValueError("El almacén de origen y destino deben ser distintos")

    default_id = await _default_warehouse_id(db, tenant_id)
    available = await _available_in(db, tenant_id, product_id, from_warehouse_id, default_id)
    if qty > available:
        raise ValueError(f"Stock insuficiente en el almacén de origen ({available} < {qty})")

    # Agregado: solo se escriben filas de almacenes NO-default (el default se deriva).
    if from_warehouse_id != default_id:
        await _set_nondefault(
            db, tenant_id=tenant_id, product_id=product_id, warehouse_id=from_warehouse_id, delta=-qty
        )
    if to_warehouse_id != default_id:
        await _set_nondefault(db, tenant_id=tenant_id, product_id=product_id, warehouse_id=to_warehouse_id, delta=qty)

    # Lotes en el origen (los del almacén origen; si origen es default, también los NULL).
    cond = ProductLot.warehouse_id == from_warehouse_id
    if default_id is not None and from_warehouse_id == default_id:
        cond = (ProductLot.warehouse_id == from_warehouse_id) | (ProductLot.warehouse_id.is_(None))
    lots_res = await db.execute(
        select(ProductLot).where(ProductLot.product_id == product_id, ProductLot.quantity > 0, cond)
    )
    origin_lots = list(lots_res.scalars().all())
    moved_lots: list[dict] = []
    if origin_lots:
        plan, _shortage = plan_fefo_deduction(origin_lots, qty)
        by_id = {lot.id: lot for lot in origin_lots}
        for alloc in plan:
            lot = by_id[alloc.lot_id]
            if alloc.quantity >= int(lot.quantity):
                lot.warehouse_id = to_warehouse_id
            else:
                lot.quantity = int(lot.quantity) - alloc.quantity
                db.add(
                    ProductLot(
                        tenant_id=tenant_id,
                        product_id=product_id,
                        warehouse_id=to_warehouse_id,
                        lot_number=lot.lot_number,
                        expiry_date=lot.expiry_date,
                        quantity=alloc.quantity,
                        cost_price=lot.cost_price,
                    )
                )
            moved_lots.append({"lot_number": lot.lot_number, "quantity": alloc.quantity})

    await db.commit()
    return {
        "product_id": str(product_id),
        "from_warehouse_id": str(from_warehouse_id),
        "to_warehouse_id": str(to_warehouse_id),
        "quantity": qty,
        "moved_lots": moved_lots,
    }
