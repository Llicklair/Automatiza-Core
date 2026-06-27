"""Invariants for stock_service.transfer() — conservation, rejection, atomicity, guards.

Four empirical invariants:
  1. CONSERVATION + happy path: default→non-default. Global total unchanged; legs correct.
  2. INSUFFICIENT-STOCK REJECTION: transfer more than available raises ValueError; no mutation.
  3. TWO-LEG ATOMICITY: non-default→non-default. Both legs commit together; global unchanged.
  4. GUARD: qty<=0 or from==to raises ValueError before any lock/mutation.
"""

from uuid import uuid4

import pytest

from app.db.models.inventory import Product, Warehouse
from app.services.inventory import stock_service

# ── helpers ────────────────────────────────────────────────────────────────────


async def _make_warehouse(db, tenant_id, *, is_default: bool, name: str) -> Warehouse:
    wh = Warehouse(
        id=uuid4(),
        tenant_id=tenant_id,
        name=name,
        is_default=is_default,
        is_active=True,
    )
    db.add(wh)
    await db.flush()
    return wh


async def _make_product(db, tenant_id, *, stock: int) -> Product:
    p = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Producto Test Transfer",
        sku=f"SKU-TR-{uuid4().hex[:6]}",
        unit="ud",
        price=10,
        stock_quantity=stock,
    )
    db.add(p)
    await db.flush()
    return p


def _qty_for(breakdown: list[dict], warehouse_id) -> int:
    wid = str(warehouse_id)
    for row in breakdown:
        if row["warehouse_id"] == wid:
            return int(row["quantity"])
    return 0


# ── Test 1: CONSERVATION + happy path (default → non-default) ─────────────────


async def test_transfer_conservation_default_to_nondefault(db, seed_tenant_and_user):
    """Transfer 30 from default→B. Global total stays 100; B==30; default derived==70."""
    tenant, _, _ = seed_tenant_and_user

    default_wh = await _make_warehouse(db, tenant.id, is_default=True, name="Principal")
    wh_b = await _make_warehouse(db, tenant.id, is_default=False, name="Almacen B")
    product = await _make_product(db, tenant.id, stock=100)

    # Capture IDs before transfer() commits (ORM attrs expire on commit)
    tid = tenant.id
    pid = product.id
    default_id = default_wh.id
    b_id = wh_b.id

    await stock_service.transfer(
        db,
        tenant_id=tid,
        product_id=pid,
        from_warehouse_id=default_id,
        to_warehouse_id=b_id,
        quantity=30,
    )

    breakdown = await stock_service.get_by_warehouse(db, tid, pid)

    assert _qty_for(breakdown, b_id) == 30, "B should have 30 after transfer"
    assert _qty_for(breakdown, default_id) == 70, "Default derived qty should be 70"

    # Global total must be unchanged
    await db.refresh(product)
    assert int(product.stock_quantity) == 100, "Global stock_quantity must remain 100"


# ── Test 2: INSUFFICIENT-STOCK REJECTION ──────────────────────────────────────


async def test_transfer_insufficient_stock_raises_no_mutation(db, seed_tenant_and_user):
    """Transfer 200 when only 100 available → ValueError; B still 0, global still 100."""
    tenant, _, _ = seed_tenant_and_user

    default_wh = await _make_warehouse(db, tenant.id, is_default=True, name="Principal")
    wh_b = await _make_warehouse(db, tenant.id, is_default=False, name="Almacen B")
    product = await _make_product(db, tenant.id, stock=100)

    # Commit setup so that rollback (after ValueError) doesn't discard these rows
    await db.commit()

    tid = tenant.id
    pid = product.id
    default_id = default_wh.id
    b_id = wh_b.id

    with pytest.raises(ValueError, match="insuficiente"):
        await stock_service.transfer(
            db,
            tenant_id=tid,
            product_id=pid,
            from_warehouse_id=default_id,
            to_warehouse_id=b_id,
            quantity=200,
        )

    # ValueError left session dirty (partial writes before the raise); rollback before reading
    await db.rollback()

    breakdown = await stock_service.get_by_warehouse(db, tid, pid)

    assert _qty_for(breakdown, b_id) == 0, "B must still be 0 after rejected transfer"
    assert _qty_for(breakdown, default_id) == 100, "Default derived qty must still be 100"

    await db.refresh(product)
    assert int(product.stock_quantity) == 100, "Global must remain 100 after rejection"


# ── Test 3: TWO-LEG ATOMICITY (non-default → non-default) ────────────────────


async def test_transfer_two_leg_atomicity_nondefault_to_nondefault(db, seed_tenant_and_user):
    """Seed A=50 (default→A), then transfer A→B 20. A==30 AND B==20 AND global==100."""
    tenant, _, _ = seed_tenant_and_user

    default_wh = await _make_warehouse(db, tenant.id, is_default=True, name="Principal")
    wh_a = await _make_warehouse(db, tenant.id, is_default=False, name="Almacen A")
    wh_b = await _make_warehouse(db, tenant.id, is_default=False, name="Almacen B")
    product = await _make_product(db, tenant.id, stock=100)

    tid = tenant.id
    pid = product.id
    default_id = default_wh.id
    a_id = wh_a.id
    b_id = wh_b.id

    # Seed A with 50 via default→A transfer
    await stock_service.transfer(
        db,
        tenant_id=tid,
        product_id=pid,
        from_warehouse_id=default_id,
        to_warehouse_id=a_id,
        quantity=50,
    )

    # Now transfer A→B 20 (non-default → non-default)
    await stock_service.transfer(
        db,
        tenant_id=tid,
        product_id=pid,
        from_warehouse_id=a_id,
        to_warehouse_id=b_id,
        quantity=20,
    )

    breakdown = await stock_service.get_by_warehouse(db, tid, pid)

    assert _qty_for(breakdown, a_id) == 30, "A should have 30 after transferring 20 away"
    assert _qty_for(breakdown, b_id) == 20, "B should have 20 after receiving from A"
    assert _qty_for(breakdown, default_id) == 50, "Default derived qty should remain 50"

    await db.refresh(product)
    assert int(product.stock_quantity) == 100, "Global must remain 100 throughout"


# ── Test 4: GUARDS — qty<=0 and from==to ─────────────────────────────────────


async def test_transfer_guard_zero_quantity(db, seed_tenant_and_user):
    """qty=0 raises ValueError before any lock or mutation."""
    tenant, _, _ = seed_tenant_and_user

    default_wh = await _make_warehouse(db, tenant.id, is_default=True, name="Principal")
    wh_b = await _make_warehouse(db, tenant.id, is_default=False, name="Almacen B")
    product = await _make_product(db, tenant.id, stock=100)

    with pytest.raises(ValueError, match="mayor que cero"):
        await stock_service.transfer(
            db,
            tenant_id=tenant.id,
            product_id=product.id,
            from_warehouse_id=default_wh.id,
            to_warehouse_id=wh_b.id,
            quantity=0,
        )


async def test_transfer_guard_negative_quantity(db, seed_tenant_and_user):
    """qty=-5 raises ValueError before any lock or mutation."""
    tenant, _, _ = seed_tenant_and_user

    default_wh = await _make_warehouse(db, tenant.id, is_default=True, name="Principal")
    wh_b = await _make_warehouse(db, tenant.id, is_default=False, name="Almacen B")
    product = await _make_product(db, tenant.id, stock=100)

    with pytest.raises(ValueError, match="mayor que cero"):
        await stock_service.transfer(
            db,
            tenant_id=tenant.id,
            product_id=product.id,
            from_warehouse_id=default_wh.id,
            to_warehouse_id=wh_b.id,
            quantity=-5,
        )


async def test_transfer_guard_same_warehouse(db, seed_tenant_and_user):
    """from==to raises ValueError before any lock or mutation."""
    tenant, _, _ = seed_tenant_and_user

    default_wh = await _make_warehouse(db, tenant.id, is_default=True, name="Principal")
    product = await _make_product(db, tenant.id, stock=100)

    with pytest.raises(ValueError, match="distintos"):
        await stock_service.transfer(
            db,
            tenant_id=tenant.id,
            product_id=product.id,
            from_warehouse_id=default_wh.id,
            to_warehouse_id=default_wh.id,
            quantity=10,
        )
