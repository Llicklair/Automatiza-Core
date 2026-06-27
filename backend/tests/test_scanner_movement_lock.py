"""Tests for record_movement after the row-lock fix in scanner.py.

These are sequential / SQLite-safe tests — they verify that the
with_for_update() + populate_existing path did NOT break record_movement
and that core stock invariants hold end-to-end.

SQLite silently ignores FOR UPDATE, so we cannot reproduce the concurrent
race here; we prove correctness of the serialized path instead.
"""
import pytest
from sqlalchemy import func, select

from app.db.models.inventory import Product, StockMovement
from app.services.documents.scanner import record_movement

# ── helper ────────────────────────────────────────────────────────────────────

async def _make_product(db, tenant_id, *, sku, barcode=None, stock):
    p = Product(
        tenant_id=tenant_id,
        name=f"Producto {sku}",
        sku=sku,
        barcode=barcode,
        stock_quantity=stock,
        price=10,
        cost_price=5,
        is_active=True,
    )
    db.add(p)
    await db.flush()
    return p


# ── 1. ENTRADA path ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_entrada_increases_stock(db, seed_tenant_and_user):
    """record_movement entrada: stock goes 10 → 15, StockMovement row created."""
    tenant, _, _ = seed_tenant_and_user
    p = await _make_product(db, tenant.id, sku="PROD-ENT", stock=10)
    product_id = p.id

    result = await record_movement(
        db,
        tenant_id=tenant.id,
        code="PROD-ENT",
        quantity=5,
        notes="",
        movement_type="entrada",
        device="dev1",
    )

    # Return value assertions
    assert result["stock_before"] == 10
    assert result["stock_after"] == 15

    # DB assertions — record_movement committed, fetch fresh
    row = await db.get(Product, product_id)
    assert float(row.stock_quantity) == 15

    mv = await db.execute(
        select(StockMovement).where(StockMovement.product_id == product_id)
    )
    movements = mv.scalars().all()
    assert len(movements) == 1
    m = movements[0]
    assert m.movement_type == "entrada"
    assert float(m.quantity) == 5
    assert float(m.stock_after) == 15
    assert m.reference == "scanner:dev1"


# ── 2. SALIDA path ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_salida_decreases_stock(db, seed_tenant_and_user):
    """record_movement salida: stock goes 10 → 7, StockMovement row created."""
    tenant, _, _ = seed_tenant_and_user
    p = await _make_product(db, tenant.id, sku="PROD-SAL", stock=10)
    product_id = p.id

    result = await record_movement(
        db,
        tenant_id=tenant.id,
        code="PROD-SAL",
        quantity=3,
        notes="",
        movement_type="salida",
        device="dev2",
    )

    assert result["stock_before"] == 10
    assert result["stock_after"] == 7

    row = await db.get(Product, product_id)
    assert float(row.stock_quantity) == 7

    mv = await db.execute(
        select(StockMovement).where(StockMovement.product_id == product_id)
    )
    movements = mv.scalars().all()
    assert len(movements) == 1
    m = movements[0]
    assert m.movement_type == "salida"
    assert float(m.quantity) == 3
    assert float(m.stock_after) == 7


# ── 3. INSUFFICIENT STOCK raises ValueError, no StockMovement ────────────────

@pytest.mark.asyncio
async def test_salida_insufficient_raises_and_no_movement(db, seed_tenant_and_user):
    """salida with qty > stock raises ValueError; stock unchanged, no row written."""
    tenant, _, _ = seed_tenant_and_user
    p = await _make_product(db, tenant.id, sku="PROD-LOW", stock=2)
    # Commit so the product survives the rollback below.
    await db.commit()
    product_id = p.id

    with pytest.raises(ValueError, match="insuficiente"):
        await record_movement(
            db,
            tenant_id=tenant.id,
            code="PROD-LOW",
            quantity=5,
            notes="",
            movement_type="salida",
            device="dev3",
        )

    # After the expected exception the transaction is aborted; roll it back
    # so we can query the DB cleanly with a fresh SELECT.
    await db.rollback()

    # Use scalar_one instead of db.get to bypass the stale identity map.
    row = (await db.execute(
        select(Product).where(Product.id == product_id)
    )).scalar_one()
    assert float(row.stock_quantity) == 2, "stock must be unchanged after failed salida"

    count = await db.scalar(
        select(func.count(StockMovement.id)).where(StockMovement.product_id == product_id)
    )
    assert count == 0, "no StockMovement row should exist after failed salida"


# ── 4. SEQUENTIAL CONSERVATION ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sequential_movements_accumulate_correctly(db, seed_tenant_and_user):
    """stock=10 → entrada 5 (=15) → salida 8 (=7); 2 rows, final stock==7."""
    tenant, _, _ = seed_tenant_and_user
    p = await _make_product(db, tenant.id, sku="PROD-SEQ", stock=10)
    product_id = p.id

    r1 = await record_movement(
        db,
        tenant_id=tenant.id,
        code="PROD-SEQ",
        quantity=5,
        notes="",
        movement_type="entrada",
        device="devA",
    )
    assert r1["stock_after"] == 15

    r2 = await record_movement(
        db,
        tenant_id=tenant.id,
        code="PROD-SEQ",
        quantity=8,
        notes="",
        movement_type="salida",
        device="devA",
    )
    assert r2["stock_after"] == 7

    row = await db.get(Product, product_id)
    assert float(row.stock_quantity) == 7

    count = await db.scalar(
        select(func.count(StockMovement.id)).where(StockMovement.product_id == product_id)
    )
    assert count == 2, "exactly 2 StockMovement rows expected"


# ── 5. LOOKUP: barcode vs SKU ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lookup_by_barcode_and_by_sku(db, seed_tenant_and_user):
    """record_movement resolves product by both barcode and SKU."""
    tenant, _, _ = seed_tenant_and_user

    # Product with both barcode and SKU
    p = await _make_product(db, tenant.id, sku="SKU-BC", barcode="1234567890123", stock=20)
    product_id = p.id

    # Lookup via barcode
    r_bc = await record_movement(
        db,
        tenant_id=tenant.id,
        code="1234567890123",
        quantity=2,
        notes="",
        movement_type="salida",
        device="devBC",
    )
    assert r_bc["stock_after"] == 18

    # Lookup via SKU
    r_sku = await record_movement(
        db,
        tenant_id=tenant.id,
        code="SKU-BC",
        quantity=3,
        notes="",
        movement_type="entrada",
        device="devSKU",
    )
    assert r_sku["stock_after"] == 21

    row = await db.get(Product, product_id)
    assert float(row.stock_quantity) == 21

    count = await db.scalar(
        select(func.count(StockMovement.id)).where(StockMovement.product_id == product_id)
    )
    assert count == 2
