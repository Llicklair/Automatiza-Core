"""Analítica de inventario: valoración, stock muerto y productos más movidos.

Complementa la analítica de negocio (ingresos/márgenes) con métricas propias de
almacén, a partir de Product y StockMovement.

No lanza HTTPException — solo excepciones Python o valores de retorno.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.inventory import Product, StockMovement


async def _valuation(db: AsyncSession, tenant_id: UUID) -> dict:
    """Valoración del stock a coste y a PVP (productos activos con stock)."""
    res = await db.execute(
        select(
            func.coalesce(func.sum(Product.stock_quantity * Product.cost_price), 0),
            func.coalesce(func.sum(Product.stock_quantity * Product.price), 0),
            func.coalesce(func.sum(Product.stock_quantity), 0),
            func.count(Product.id),
        ).where(
            Product.tenant_id == tenant_id,
            Product.is_active.is_(True),
            Product.stock_quantity > 0,
        )
    )
    cost, retail, units, count = res.one()
    cost = float(cost or 0)
    retail = float(retail or 0)
    return {
        "value_cost": round(cost, 2),
        "value_retail": round(retail, 2),
        "potential_margin": round(retail - cost, 2),
        "units": int(units or 0),
        "product_count": int(count or 0),
    }


async def _top_movers(db: AsyncSession, tenant_id: UUID, days: int, limit: int) -> list[dict]:
    """Productos con más VENTAS (unidades) en los últimos `days` días.

    Excluye bajas (mermas/roturas/etc.: `reason IS NOT NULL`) y movimientos de
    cajas (`stock_kind != 'unit'`) para no contaminar las ventas reales.
    """
    cutoff = datetime.now(UTC) - timedelta(days=max(1, days))
    sold = func.sum(func.abs(StockMovement.quantity))
    res = await db.execute(
        select(Product.id, Product.name, Product.sku, sold.label("sold"))
        .join(StockMovement, StockMovement.product_id == Product.id)
        .where(
            StockMovement.tenant_id == tenant_id,
            StockMovement.movement_type == "salida",
            StockMovement.reason.is_(None),
            StockMovement.stock_kind == "unit",
            StockMovement.created_at >= cutoff,
        )
        .group_by(Product.id, Product.name, Product.sku)
        .order_by(sold.desc())
        .limit(limit)
    )
    return [{"product_id": str(pid), "name": name, "sku": sku, "sold": int(s or 0)} for pid, name, sku, s in res.all()]


async def _dead_stock(db: AsyncSession, tenant_id: UUID, days: int) -> list[dict]:
    """Productos con stock pero sin ninguna salida en los últimos `days` días."""
    cutoff = datetime.now(UTC) - timedelta(days=max(1, days))
    last_out = (
        select(
            StockMovement.product_id.label("pid"),
            func.max(StockMovement.created_at).label("last_out"),
        )
        .where(StockMovement.tenant_id == tenant_id, StockMovement.movement_type == "salida")
        .group_by(StockMovement.product_id)
        .subquery()
    )
    res = await db.execute(
        select(Product, last_out.c.last_out)
        .outerjoin(last_out, last_out.c.pid == Product.id)
        .where(
            Product.tenant_id == tenant_id,
            Product.is_active.is_(True),
            Product.stock_quantity > 0,
        )
    )
    now = datetime.now(UTC)
    out: list[dict] = []
    for product, lo in res.all():
        if lo is not None and lo >= cutoff:
            continue  # tuvo salida reciente → no es stock muerto
        days_since = (now - lo).days if lo is not None else None
        out.append(
            {
                "product_id": str(product.id),
                "name": product.name,
                "sku": product.sku,
                "stock": int(product.stock_quantity or 0),
                "last_sale": lo.isoformat() if lo is not None else None,
                "days_since_sale": days_since,
                "value_cost": round(float(product.stock_quantity or 0) * float(product.cost_price or 0), 2),
            }
        )
    out.sort(key=lambda d: d["value_cost"], reverse=True)
    return out


async def _bajas(db: AsyncSession, tenant_id: UUID, days: int) -> dict:
    """Resumen de bajas (mermas/roturas/robos/caducados) de UNIDADES en `days` días.

    Una baja = salida con `reason` no nulo. Sólo `stock_kind == 'unit'` (las cajas
    se reportan aparte en `box_bajas_units`). El valor usa `unit_cost` del
    movimiento si existe, si no el `cost_price` del producto, si no 0.
    """
    cutoff = datetime.now(UTC) - timedelta(days=max(1, days))
    units = func.abs(StockMovement.quantity)
    cost = func.coalesce(StockMovement.unit_cost, Product.cost_price, 0)
    value = units * cost

    base_filter = (
        StockMovement.tenant_id == tenant_id,
        StockMovement.movement_type == "salida",
        StockMovement.reason.is_not(None),
        StockMovement.stock_kind == "unit",
        StockMovement.created_at >= cutoff,
    )

    totals_res = await db.execute(
        select(
            func.coalesce(func.sum(units), 0),
            func.coalesce(func.sum(value), 0),
        )
        .select_from(StockMovement)
        .join(Product, Product.id == StockMovement.product_id)
        .where(*base_filter)
    )
    total_units, total_value = totals_res.one()

    by_reason_res = await db.execute(
        select(
            StockMovement.reason,
            func.coalesce(func.sum(units), 0),
            func.coalesce(func.sum(value), 0),
        )
        .select_from(StockMovement)
        .join(Product, Product.id == StockMovement.product_id)
        .where(*base_filter)
        .group_by(StockMovement.reason)
        .order_by(func.sum(value).desc())
    )
    by_reason = [
        {"reason": reason, "units": int(u or 0), "value_eur": round(float(v or 0), 2)}
        for reason, u, v in by_reason_res.all()
    ]

    top_res = await db.execute(
        select(
            Product.id,
            Product.name,
            func.coalesce(func.sum(units), 0).label("units"),
            func.coalesce(func.sum(value), 0).label("value"),
        )
        .select_from(StockMovement)
        .join(Product, Product.id == StockMovement.product_id)
        .where(*base_filter)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(value).desc())
        .limit(5)
    )
    top_products = [
        {"product_id": str(pid), "name": name, "units": int(u or 0), "value_eur": round(float(v or 0), 2)}
        for pid, name, u, v in top_res.all()
    ]

    return {
        "period_days": days,
        "total_units": int(total_units or 0),
        "total_value_eur": round(float(total_value or 0), 2),
        "by_reason": by_reason,
        "top_products": top_products,
    }


async def _box_bajas_units(db: AsyncSession, tenant_id: UUID, days: int) -> int:
    """Total de unidades de CAJAS dadas de baja en `days` días (sin conversión)."""
    cutoff = datetime.now(UTC) - timedelta(days=max(1, days))
    res = await db.execute(
        select(func.coalesce(func.sum(func.abs(StockMovement.quantity)), 0)).where(
            StockMovement.tenant_id == tenant_id,
            StockMovement.movement_type == "salida",
            StockMovement.reason.is_not(None),
            StockMovement.stock_kind == "box",
            StockMovement.created_at >= cutoff,
        )
    )
    return int(res.scalar() or 0)


async def _below_min(db: AsyncSession, tenant_id: UUID) -> dict:
    """Productos activos en/bajo su punto de pedido (`stock_min_alert`)."""
    res = await db.execute(
        select(
            func.count(Product.id),
            func.coalesce(func.sum(Product.stock_quantity * func.coalesce(Product.cost_price, 0)), 0),
        ).where(
            Product.tenant_id == tenant_id,
            Product.is_active.is_(True),
            Product.stock_min_alert > 0,
            Product.stock_quantity <= Product.stock_min_alert,
        )
    )
    count, value = res.one()
    return {"count": int(count or 0), "value_eur": round(float(value or 0), 2)}


async def inventory_overview(
    db: AsyncSession,
    tenant_id: UUID,
    dead_days: int = 90,
    top_days: int = 30,
    merma_days: int = 30,
) -> dict:
    """Resumen de analítica de inventario para el panel."""
    valuation = await _valuation(db, tenant_id)
    dead = await _dead_stock(db, tenant_id, dead_days)
    top = await _top_movers(db, tenant_id, top_days, limit=15)
    bajas = await _bajas(db, tenant_id, merma_days)
    box_bajas_units = await _box_bajas_units(db, tenant_id, merma_days)
    below_min = await _below_min(db, tenant_id)
    return {
        "valuation": valuation,
        "dead_days": dead_days,
        "top_days": top_days,
        "merma_days": merma_days,
        "dead_count": len(dead),
        "dead_value_cost": round(sum(d["value_cost"] for d in dead), 2),
        "dead_stock": dead[:50],
        "top_movers": top,
        "bajas": bajas,
        "box_bajas_units": box_bajas_units,
        "below_min": below_min,
    }
