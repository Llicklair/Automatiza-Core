"""Tests de analítica de bajas/mermas y stock bajo mínimo (BD SQLite de test).

Cubren `inventory_overview`:
- `bajas`: agregación por motivo (by_reason) y valor (unit_cost → cost_price).
- `box_bajas_units`: las bajas de cajas se reportan aparte, sin convertir a unidades.
- `below_min`: productos activos en/bajo `stock_min_alert`.
- `top_movers` ahora EXCLUYE bajas (reason no nulo) y movimientos de cajas.
"""
from datetime import UTC, datetime, timedelta

import pytest

from app.db.models.inventory import Product, StockMovement
from app.services.inventory import analytics


async def _add_product(db, tenant_id, **kw):
    p = Product(
        tenant_id=tenant_id,
        name=kw.get("name", "Producto"),
        sku=kw.get("sku"),
        stock_quantity=kw.get("stock_quantity", 0),
        stock_min_alert=kw.get("stock_min_alert", 0),
        price=kw.get("price", 10),
        cost_price=kw.get("cost_price", 5),
        is_active=kw.get("is_active", True),
    )
    db.add(p)
    await db.flush()
    return p


async def _add_movement(db, tenant_id, product_id, **kw):
    m = StockMovement(
        tenant_id=tenant_id,
        product_id=product_id,
        movement_type=kw.get("movement_type", "salida"),
        stock_kind=kw.get("stock_kind", "unit"),
        reason=kw.get("reason"),
        quantity=kw.get("quantity", -1),
        stock_after=kw.get("stock_after", 0),
        unit_cost=kw.get("unit_cost"),
        created_at=kw.get("created_at", datetime.now(UTC)),
    )
    db.add(m)
    await db.flush()
    return m


@pytest.mark.asyncio
async def test_bajas_by_reason_and_value(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    p = await _add_product(db, tenant.id, name="Yogur", cost_price=2)
    # 3 ud rotas @ unit_cost 3 = 9 €; 2 ud caducadas sin unit_cost → cost_price 2 = 4 €
    await _add_movement(db, tenant.id, p.id, reason="rotura", quantity=-3, unit_cost=3)
    await _add_movement(db, tenant.id, p.id, reason="caducado", quantity=-2)
    # Venta normal: NO es baja (reason null) → no debe contar.
    await _add_movement(db, tenant.id, p.id, reason=None, quantity=-5)
    await db.commit()

    out = await analytics.inventory_overview(db, tenant.id)
    bajas = out["bajas"]

    assert bajas["period_days"] == 30
    assert bajas["total_units"] == 5
    assert bajas["total_value_eur"] == 13.0  # 9 + 4

    by_reason = {r["reason"]: r for r in bajas["by_reason"]}
    assert by_reason["rotura"]["units"] == 3
    assert by_reason["rotura"]["value_eur"] == 9.0
    assert by_reason["caducado"]["units"] == 2
    assert by_reason["caducado"]["value_eur"] == 4.0

    assert bajas["top_products"][0]["product_id"] == str(p.id)
    assert bajas["top_products"][0]["value_eur"] == 13.0


@pytest.mark.asyncio
async def test_bajas_excludes_old_movements(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    p = await _add_product(db, tenant.id, cost_price=2)
    old = datetime.now(UTC) - timedelta(days=40)
    await _add_movement(db, tenant.id, p.id, reason="merma", quantity=-4, created_at=old)
    await db.commit()

    out = await analytics.inventory_overview(db, tenant.id, merma_days=30)
    assert out["bajas"]["total_units"] == 0
    # Pero con ventana más amplia sí entra.
    out2 = await analytics.inventory_overview(db, tenant.id, merma_days=90)
    assert out2["bajas"]["total_units"] == 4


@pytest.mark.asyncio
async def test_box_bajas_reported_separately(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    p = await _add_product(db, tenant.id, cost_price=10)
    await _add_movement(db, tenant.id, p.id, reason="rotura", quantity=-2, stock_kind="box")
    await _add_movement(db, tenant.id, p.id, reason="rotura", quantity=-1, stock_kind="unit", unit_cost=10)
    await db.commit()

    out = await analytics.inventory_overview(db, tenant.id)
    # Las cajas NO entran en `bajas` (unit-only)…
    assert out["bajas"]["total_units"] == 1
    assert out["bajas"]["total_value_eur"] == 10.0
    # …se reportan aparte sin conversión.
    assert out["box_bajas_units"] == 2


@pytest.mark.asyncio
async def test_below_min(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    # En/bajo mínimo (cuenta): stock 3 <= min 5, coste 4 → 12 €
    await _add_product(db, tenant.id, name="Bajo", stock_quantity=3, stock_min_alert=5, cost_price=4)
    # Por encima del mínimo: no cuenta.
    await _add_product(db, tenant.id, name="OK", stock_quantity=20, stock_min_alert=5, cost_price=4)
    # Sin alerta configurada (min 0): no cuenta.
    await _add_product(db, tenant.id, name="SinAlerta", stock_quantity=0, stock_min_alert=0, cost_price=4)
    # Inactivo bajo mínimo: no cuenta.
    await _add_product(
        db, tenant.id, name="Inactivo", stock_quantity=1, stock_min_alert=5, cost_price=4, is_active=False
    )
    await db.commit()

    out = await analytics.inventory_overview(db, tenant.id)
    assert out["below_min"]["count"] == 1
    assert out["below_min"]["value_eur"] == 12.0


@pytest.mark.asyncio
async def test_top_movers_excludes_writeoffs_and_boxes(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    p = await _add_product(db, tenant.id, name="Camiseta")
    # Venta real (cuenta): 7 ud.
    await _add_movement(db, tenant.id, p.id, reason=None, stock_kind="unit", quantity=-7)
    # Baja por robo (NO cuenta como venta).
    await _add_movement(db, tenant.id, p.id, reason="robo", stock_kind="unit", quantity=-100)
    # Movimiento de cajas (NO cuenta).
    await _add_movement(db, tenant.id, p.id, reason=None, stock_kind="box", quantity=-50)
    await db.commit()

    out = await analytics.inventory_overview(db, tenant.id, top_days=30)
    movers = {m["product_id"]: m for m in out["top_movers"]}
    assert movers[str(p.id)]["sold"] == 7
