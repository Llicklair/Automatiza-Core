"""Gestión de lotes de producto y deducción FEFO sobre la base de datos.

Capa OPCIONAL sobre el inventario: si un producto no tiene lotes, nada de esto
se ejecuta y el stock funciona como siempre. Cuando hay lotes, la salida
descuenta primero el que caduca antes (FEFO).

No lanza HTTPException — solo excepciones Python o valores de retorno.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.inventory import Product, ProductLot
from app.services.alerts._expiry import expiry_status

from ._fefo import plan_fefo_deduction

logger = logging.getLogger(__name__)

# Campos del lote editables por el CRUD de gestión (NO incluye quantity: la
# cantidad solo cambia vía movimientos de stock, para no descuadrar el agregado).
_EDITABLE_FIELDS = {"lot_number", "expiry_date", "cost_price"}


async def _load_lots(db: AsyncSession, product_id: UUID) -> list[ProductLot]:
    result = await db.execute(
        select(ProductLot).where(
            ProductLot.product_id == product_id,
            ProductLot.quantity > 0,
        )
    )
    return list(result.scalars().all())


def _lot_dict(lot: ProductLot) -> dict:
    return {
        "id": str(lot.id),
        "product_id": str(lot.product_id),
        "lot_number": lot.lot_number,
        "expiry_date": lot.expiry_date.isoformat() if lot.expiry_date else None,
        "quantity": int(lot.quantity),
        "cost_price": float(lot.cost_price) if lot.cost_price is not None else None,
        "received_at": lot.received_at.isoformat() if lot.received_at else None,
    }


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


# ── Gestión (API) ─────────────────────────────────────────────────────────────


async def _get_product_owned(db: AsyncSession, tenant_id: UUID, product_id: UUID) -> Product:
    result = await db.execute(select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id))
    product = result.scalars().first()
    if product is None:
        raise LookupError(f"Producto {product_id} no encontrado")
    return product


async def list_lots(db: AsyncSession, tenant_id: UUID, product_id: UUID) -> list[dict]:
    """Lista los lotes con stock de un producto, en orden de caducidad (FEFO)."""
    await _get_product_owned(db, tenant_id, product_id)
    result = await db.execute(
        select(ProductLot).where(
            ProductLot.tenant_id == tenant_id,
            ProductLot.product_id == product_id,
            ProductLot.quantity > 0,
        )
    )
    lots = list(result.scalars().all())
    lots.sort(key=lambda lot: (lot.expiry_date is None, lot.expiry_date or date.max))
    return [_lot_dict(lot) for lot in lots]


async def update_lot_metadata(db: AsyncSession, tenant_id: UUID, lot_id: UUID, fields: dict) -> dict:
    """Edita metadatos de un lote (número, caducidad, coste).

    NO modifica la cantidad: el stock solo cambia por movimientos, para no
    descuadrar `Product.stock_quantity`.
    """
    result = await db.execute(select(ProductLot).where(ProductLot.id == lot_id, ProductLot.tenant_id == tenant_id))
    lot = result.scalars().first()
    if lot is None:
        raise LookupError(f"Lote {lot_id} no encontrado")

    for key, value in fields.items():
        if key in _EDITABLE_FIELDS:
            setattr(lot, key, value)

    await db.commit()
    return _lot_dict(lot)


async def list_expiring_lots(db: AsyncSession, tenant_id: UUID, days: int = 7) -> list[dict]:
    """Lotes con stock que caducan dentro de `days` días (o ya caducados).

    Pensado para un panel de control: incluye nombre de producto, severidad y
    días restantes (negativos si ya caducó).
    """
    today = datetime.now(UTC).date()
    horizon = today + timedelta(days=max(0, int(days)))
    result = await db.execute(
        select(ProductLot, Product.name)
        .join(Product, ProductLot.product_id == Product.id)
        .where(
            ProductLot.tenant_id == tenant_id,
            ProductLot.quantity > 0,
            ProductLot.expiry_date.is_not(None),
            ProductLot.expiry_date <= horizon,
        )
        .order_by(ProductLot.expiry_date.asc())
    )
    out: list[dict] = []
    for lot, product_name in result.all():
        severity, days_left = expiry_status(lot.expiry_date, today)
        entry = _lot_dict(lot)
        entry.update(
            {
                "product_name": product_name,
                "severity": severity,
                "days_left": days_left,
            }
        )
        out.append(entry)
    return out


async def create_lot(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    product_id: UUID,
    lot_number: str,
    quantity: int,
    expiry_date: date | None = None,
    cost_price: float | None = None,
) -> dict:
    """Da de alta un lote desde la gestión de escritorio (recepción manual).

    A diferencia de `add_lot`, aquí SÍ se reconcilia el agregado: suma la
    cantidad a `Product.stock_quantity` y registra un movimiento de entrada
    para mantener la trazabilidad. Todo en la misma transacción.
    """
    from app.db.models.inventory import StockMovement

    product = await _get_product_owned(db, tenant_id, product_id)
    qty = abs(int(quantity))
    if qty <= 0:
        raise ValueError("La cantidad debe ser mayor que cero")

    await add_lot(
        db,
        tenant_id=tenant_id,
        product_id=product_id,
        lot_number=lot_number,
        quantity=qty,
        expiry_date=expiry_date,
        cost_price=cost_price,
    )

    new_stock = int(product.stock_quantity or 0) + qty
    product.stock_quantity = new_stock

    nota = f"Alta de lote {lot_number}"
    if expiry_date:
        nota += f" (cad. {expiry_date.isoformat()})"
    movement = StockMovement(
        product_id=product.id,
        movement_type="entrada",
        quantity=qty,
        stock_after=new_stock,
        unit_cost=cost_price,
        reference=f"lote:{lot_number}",
        notes=nota,
    )
    db.add(movement)
    await db.commit()

    return {"stock_after": new_stock, "lots": await list_lots(db, tenant_id, product_id)}
