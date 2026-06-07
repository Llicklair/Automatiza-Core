"""Tests del servicio batch de inventario (con BD SQLite de test).

Cubren lo crítico de las modificaciones por lotes: la PREVISUALIZACIÓN (dry_run)
no debe tocar la BD, la aplicación sí, y debe registrar StockMovement; además la
resolución de productos y las validaciones de campos.
"""
import pytest
from sqlalchemy import func, select

from app.db.models.inventory import Product, StockMovement
from app.services.inventory import batch_service


async def _add_product(db, tenant_id, **kw):
    p = Product(
        tenant_id=tenant_id,
        name=kw.get("name", "Producto"),
        sku=kw.get("sku"),
        stock_quantity=kw.get("stock_quantity", 0),
        price=kw.get("price", 10),
        cost_price=kw.get("cost_price", 5),
        category=kw.get("category"),
        is_active=kw.get("is_active", True),
    )
    db.add(p)
    await db.flush()
    return p


# ── resolve_product ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_by_sku_and_name(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    p = await _add_product(db, tenant.id, name="Café molido", sku="CAF-01")

    found, how = await batch_service.resolve_product(db, tenant.id, "CAF-01")
    assert found is not None and found.id == p.id and how == "sku/barcode"

    found2, _ = await batch_service.resolve_product(db, tenant.id, "Café molido")
    assert found2 is not None and found2.id == p.id


@pytest.mark.asyncio
async def test_resolve_ambiguous_name_returns_none(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    await _add_product(db, tenant.id, name="Agua 1L", sku="A1")
    await _add_product(db, tenant.id, name="Agua 2L", sku="A2")

    found, how = await batch_service.resolve_product(db, tenant.id, "Agua")
    assert found is None
    assert "ambiguo" in how


# ── batch_adjust_stock: preview vs apply ──────────────────────────────────────

@pytest.mark.asyncio
async def test_adjust_set_preview_does_not_persist(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    p = await _add_product(db, tenant.id, name="Sillas", sku="SIL-1", stock_quantity=10)

    res = await batch_service.batch_adjust_stock(
        db, tenant.id, [{"ref": "SIL-1", "quantity": 50}], op="set", dry_run=True
    )
    assert res["dry_run"] is True
    assert res["plan"][0]["before"] == 10
    assert res["plan"][0]["after"] == 50
    # No se ha tocado la BD.
    assert int(p.stock_quantity) == 10
    movements = await db.scalar(select(func.count(StockMovement.id)))
    assert movements == 0


@pytest.mark.asyncio
async def test_adjust_set_apply_persists_and_logs_movement(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    p = await _add_product(db, tenant.id, name="Mesas", sku="MES-1", stock_quantity=10)

    res = await batch_service.batch_adjust_stock(
        db, tenant.id, [{"ref": "MES-1", "quantity": 50}], op="set",
        reason="recuento anual", dry_run=False,
    )
    assert res["applied"] == 1
    await db.refresh(p)
    assert int(p.stock_quantity) == 50

    mv = (await db.execute(select(StockMovement))).scalars().all()
    assert len(mv) == 1
    assert mv[0].movement_type == "ajuste"
    assert mv[0].stock_after == 50
    # Convención "ajuste" (igual que el modal de stock): quantity = nuevo total.
    assert mv[0].quantity == 50


@pytest.mark.asyncio
async def test_entrada_logs_magnitude_not_total(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    p = await _add_product(db, tenant.id, name="Cajas", sku="CAJ-1", stock_quantity=10)

    await batch_service.batch_adjust_stock(
        db, tenant.id, [{"ref": "CAJ-1", "quantity": 5}], op="add", dry_run=False,
    )
    await db.refresh(p)
    assert int(p.stock_quantity) == 15
    mv = (await db.execute(select(StockMovement))).scalars().all()
    assert mv[0].movement_type == "entrada"
    assert mv[0].quantity == 5  # uds. movidas (magnitud), no el total
    assert mv[0].stock_after == 15


@pytest.mark.asyncio
async def test_adjust_remove_below_zero_is_skipped(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    p = await _add_product(db, tenant.id, name="Vasos", sku="VAS-1", stock_quantity=5)

    res = await batch_service.batch_adjust_stock(
        db, tenant.id, [{"ref": "VAS-1", "quantity": 10}], op="remove", dry_run=False,
    )
    assert res["ok"] == 0 and res["skipped"] == 1
    assert "negativo" in res["plan"][0]["warning"]
    await db.refresh(p)
    assert int(p.stock_quantity) == 5  # sin cambios


@pytest.mark.asyncio
async def test_adjust_unknown_ref_is_skipped(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    res = await batch_service.batch_adjust_stock(
        db, tenant.id, [{"ref": "NO-EXISTE", "quantity": 5}], op="add", dry_run=True,
    )
    assert res["ok"] == 0
    assert res["plan"][0]["status"] == "skipped"


# ── batch_update_fields ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_fields_preview_then_apply(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    p = await _add_product(db, tenant.id, name="Pan", sku="PAN-1", price=1)

    preview = await batch_service.batch_update_fields(
        db, tenant.id, [{"ref": "PAN-1", "fields": {"price": 1.5, "category": "Panadería"}}],
        dry_run=True,
    )
    assert preview["plan"][0]["changes"]["price"]["after"] == 1.5
    await db.refresh(p)
    assert float(p.price) == 1.0  # preview no aplica

    applied = await batch_service.batch_update_fields(
        db, tenant.id, [{"ref": "PAN-1", "fields": {"price": 1.5, "category": "Panadería"}}],
        dry_run=False,
    )
    assert applied["applied"] == 1
    await db.refresh(p)
    assert float(p.price) == 1.5
    assert p.category == "Panadería"


@pytest.mark.asyncio
async def test_update_rejects_unknown_field(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    await _add_product(db, tenant.id, name="X", sku="X-1")
    res = await batch_service.batch_update_fields(
        db, tenant.id, [{"ref": "X-1", "fields": {"nombre_secreto": "z"}}], dry_run=True,
    )
    assert res["plan"][0]["status"] == "error"
    assert "no editables" in res["plan"][0]["warning"]


@pytest.mark.asyncio
async def test_update_rejects_negative_price(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    await _add_product(db, tenant.id, name="Y", sku="Y-1")
    res = await batch_service.batch_update_fields(
        db, tenant.id, [{"ref": "Y-1", "fields": {"price": -3}}], dry_run=True,
    )
    assert res["plan"][0]["status"] == "error"
    assert "negativo" in res["plan"][0]["warning"]
