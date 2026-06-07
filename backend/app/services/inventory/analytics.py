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
    """Productos con más salidas (unidades) en los últimos `days` días."""
    cutoff = datetime.now(UTC) - timedelta(days=max(1, days))
    sold = func.sum(func.abs(StockMovement.quantity))
    res = await db.execute(
        select(Product.id, Product.name, Product.sku, sold.label("sold"))
        .join(StockMovement, StockMovement.product_id == Product.id)
        .where(
            StockMovement.tenant_id == tenant_id,
            StockMovement.movement_type == "salida",
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


async def inventory_overview(db: AsyncSession, tenant_id: UUID, dead_days: int = 90, top_days: int = 30) -> dict:
    """Resumen de analítica de inventario para el panel."""
    valuation = await _valuation(db, tenant_id)
    dead = await _dead_stock(db, tenant_id, dead_days)
    top = await _top_movers(db, tenant_id, top_days, limit=15)
    return {
        "valuation": valuation,
        "dead_days": dead_days,
        "top_days": top_days,
        "dead_count": len(dead),
        "dead_value_cost": round(sum(d["value_cost"] for d in dead), 2),
        "dead_stock": dead[:50],
        "top_movers": top,
    }
