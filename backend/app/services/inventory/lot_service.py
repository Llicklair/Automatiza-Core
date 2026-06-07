"""Gestión de lotes de producto y deducción FEFO sobre la base de datos.

Capa OPCIONAL sobre el inventario: si un producto no tiene lotes, nada de esto
se ejecuta y el stock funciona como siempre. Cuando hay lotes, la salida
descuenta primero el que caduca antes (FEFO).

No lanza HTTPException — solo excepciones Python o valores de retorno.
"""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.inventory import ProductLot

from ._fefo import plan_fefo_deduction

logger = logging.getLogger(__name__)


async def _load_lots(db: AsyncSession, product_id: UUID) -> list[ProductLot]:
    result = await db.execute(
        select(ProductLot).where(
            ProductLot.product_id == product_id,
            ProductLot.quantity > 0,
        )
    )
    return list(result.scalars().all())


async def has_lots(db: AsyncSession, product_id: UUID) -> bool:
    """¿El producto gestiona stock por lotes? (tiene al menos un lote con stock)."""
    result = await db.execute(
        select(ProductLot.id)
        .where(
            ProductLot.product_id == product_id,
            ProductLot.quantity > 0,
        )
        .limit(1)
    )
    return result.scalars().first() is not None


async def add_lot(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    product_id: UUID,
    lot_number: str,
    quantity: int,
    expiry_date: date | None = None,
    cost_price: float | None = None,
) -> ProductLot:
    """Crea un lote o suma cantidad a uno existente (mismo número y caducidad).

    NO toca `Product.stock_quantity`: de eso se encarga el llamador (el servicio
    de movimientos), para mantener una única fuente de verdad del agregado.
    """
    qty = abs(int(quantity))
    result = await db.execute(
        select(ProductLot).where(
            ProductLot.product_id == product_id,
            ProductLot.lot_number == lot_number,
            ProductLot.expiry_date == expiry_date,
        )
    )
    lot = result.scalars().first()
    if lot is not None:
        lot.quantity = int(lot.quantity or 0) + qty
        if cost_price is not None:
            lot.cost_price = cost_price
        return lot

    lot = ProductLot(
        tenant_id=tenant_id,
        product_id=product_id,
        lot_number=lot_number,
        expiry_date=expiry_date,
        quantity=qty,
        cost_price=cost_price,
    )
    db.add(lot)
    return lot


async def deduct_fefo(db: AsyncSession, *, product_id: UUID, quantity: int) -> dict:
    """Descuenta `quantity` unidades en orden FEFO de los lotes del producto.

    Devuelve un resumen: lotes afectados y `shortage` (lo que no se pudo cubrir
    con lotes, p.ej. por desfase entre stock agregado y lotes). No falla por
    desfase: descuenta lo disponible y deja constancia en el log.
    """
    lots = await _load_lots(db, product_id)
    if not lots:
        return {"deducted": [], "shortage": int(quantity)}

    by_id = {lot.id: lot for lot in lots}
    plan, shortage = plan_fefo_deduction(lots, quantity)

    deducted = []
    for alloc in plan:
        lot = by_id[alloc.lot_id]
        lot.quantity = int(lot.quantity) - alloc.quantity
        deducted.append(
            {
                "lot_number": lot.lot_number,
                "expiry_date": lot.expiry_date.isoformat() if lot.expiry_date else None,
                "quantity": alloc.quantity,
            }
        )

    # Limpia lotes agotados.
    for lot in lots:
        if int(lot.quantity) <= 0:
            await db.delete(lot)

    if shortage > 0:
        logger.warning(
            "FEFO: desfase de stock en producto %s — faltan %s uds en lotes",
            product_id,
            shortage,
        )

    return {"deducted": deducted, "shortage": shortage}


async def lot_summary(db: AsyncSession, product_id: UUID) -> dict | None:
    """Resumen de lotes para mostrar al escanear: total y próxima caducidad.

    Devuelve None si el producto no gestiona lotes.
    """
    lots = await _load_lots(db, product_id)
    if not lots:
        return None

    with_expiry = [lot for lot in lots if lot.expiry_date is not None]
    next_expiry = min((lot.expiry_date for lot in with_expiry), default=None)
    return {
        "count": len(lots),
        "total_quantity": sum(int(lot.quantity) for lot in lots),
        "next_expiry": next_expiry.isoformat() if next_expiry else None,
    }
