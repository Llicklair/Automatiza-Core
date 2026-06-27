"""Invariants for purchase_receiving.receive() — partial/complete/cap logic.

Three empirical invariants tested with a real Product + Warehouse so that
stock_service.add_to_warehouse() is exercised end-to-end:

  1. PARTIAL then COMPLETE: accumulation adds up to exactly the ordered qty;
     status transitions draft → partially_received → received.
  2. OVER-RECEIVE CAP: requesting more than remaining silently caps to remaining;
     stock increases by exactly the capped amount.
  3. ALREADY-RECEIVED GUARD: a second receive on a fully-received order raises
     ValueError before touching stock.
"""

from uuid import uuid4

import pytest

from app.db.models.crm import Client
from app.db.models.inventory import Product, Warehouse
from app.db.models.orders import PurchaseOrder, PurchaseOrderLine
from app.services.sales import purchase_receiving

# ── helpers ────────────────────────────────────────────────────────────────────

async def _make_warehouse(db, tenant_id) -> Warehouse:
    wh = Warehouse(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Almacén Principal Test",
        is_default=True,
        is_active=True,
    )
    db.add(wh)
    await db.flush()
    return wh


async def _make_product(db, tenant_id, initial_stock: int = 0) -> Product:
    product = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Producto Test Recepción",
        sku=f"SKU-TEST-{uuid4().hex[:6]}",
        unit="ud",
        price=10,
        stock_quantity=initial_stock,
    )
    db.add(product)
    await db.flush()
    return product


async def _make_po(db, tenant_id, product_id, ordered_qty: int, status: str = "draft"):
    supplier = Client(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Proveedor Test Stock",
        client_type="supplier",
    )
    db.add(supplier)
    await db.flush()

    po = PurchaseOrder(
        id=uuid4(),
        tenant_id=tenant_id,
        supplier_id=supplier.id,
        status=status,
        amount_base=0,
        tax_amount=0,
        amount_total=0,
    )
    db.add(po)
    await db.flush()

    line = PurchaseOrderLine(
        id=uuid4(),
        order_id=po.id,
        product_id=product_id,
        description="Línea con stock real",
        quantity=ordered_qty,
        received_quantity=0,
        unit_price=5,
        total=ordered_qty * 5,
    )
    db.add(line)
    await db.flush()
    return po, line


# ── Test 1: PARTIAL then COMPLETE ─────────────────────────────────────────────

async def test_partial_then_complete_accumulation(db, seed_tenant_and_user):
    """Receive 6/10 then 4/10 → total +10 on stock, status transitions correct."""
    tenant, _, _ = seed_tenant_and_user

    _wh = await _make_warehouse(db, tenant.id)
    product = await _make_product(db, tenant.id, initial_stock=0)
    po, line = await _make_po(db, tenant.id, product.id, ordered_qty=10)

    # Capture IDs before any commit (receive() commits internally, expiring ORM objects)
    po_id = po.id
    line_id = line.id

    # ── First receive: 6 of 10 ──
    result1 = await purchase_receiving.receive(
        db,
        tenant_id=tenant.id,
        order_id=po_id,
        receipts=[{"line_id": line_id, "quantity": 6}],
    )

    await db.refresh(line)
    await db.refresh(product)

    assert float(line.received_quantity) == 6, "received_quantity should be 6 after first receive"
    assert result1["status"] == "partially_received", "status should be partially_received after 6/10"
    assert int(product.stock_quantity) == 6, "warehouse stock should increase by exactly 6"

    # ── Second receive: 4 of remaining 4 ──
    result2 = await purchase_receiving.receive(
        db,
        tenant_id=tenant.id,
        order_id=po_id,
        receipts=[{"line_id": line_id, "quantity": 4}],
    )

    await db.refresh(line)
    await db.refresh(product)

    assert float(line.received_quantity) == 10, "received_quantity should be 10 after completing"
    assert result2["status"] == "received", "status should be received after 10/10"
    # Total stock increase must be exactly 10, not 12 or 16
    assert int(product.stock_quantity) == 10, "stock must be +10 total (not +12 or +16)"


# ── Test 2: OVER-RECEIVE CAP ──────────────────────────────────────────────────

async def test_over_receive_capped_to_remaining(db, seed_tenant_and_user):
    """Receive 8, then request 5 more → only 2 applied (remaining=2). Stock +2 not +5."""
    tenant, _, _ = seed_tenant_and_user

    _wh = await _make_warehouse(db, tenant.id)
    product = await _make_product(db, tenant.id, initial_stock=0)
    po, line = await _make_po(db, tenant.id, product.id, ordered_qty=10)

    # Capture IDs before any commit (receive() commits internally, expiring ORM objects)
    po_id = po.id
    line_id = line.id

    # Receive 8 first
    await purchase_receiving.receive(
        db,
        tenant_id=tenant.id,
        order_id=po_id,
        receipts=[{"line_id": line_id, "quantity": 8}],
    )

    await db.refresh(line)
    await db.refresh(product)
    assert float(line.received_quantity) == 8
    assert int(product.stock_quantity) == 8

    # Now request 5 but only 2 remain
    result = await purchase_receiving.receive(
        db,
        tenant_id=tenant.id,
        order_id=po_id,
        receipts=[{"line_id": line_id, "quantity": 5}],
    )

    await db.refresh(line)
    await db.refresh(product)

    assert float(line.received_quantity) == 10, "received_quantity must be capped at 10"
    assert result["status"] == "received", "status should be received after cap fills the order"
    assert int(product.stock_quantity) == 10, "stock should increase by 2 (remaining), not 5"

    # Verify the summary reports the capped quantity
    received_qty_reported = result["received"][0]["received"]
    assert float(received_qty_reported) == 2.0, f"summary must report 2 received, got {received_qty_reported}"


# ── Test 3: ALREADY-RECEIVED GUARD ────────────────────────────────────────────

async def test_receive_on_fully_received_order_raises(db, seed_tenant_and_user):
    """A second receive on an order already in 'received' status raises ValueError
    before touching stock (the status guard fires first)."""
    tenant, _, _ = seed_tenant_and_user

    _wh = await _make_warehouse(db, tenant.id)
    product = await _make_product(db, tenant.id, initial_stock=0)
    po, line = await _make_po(db, tenant.id, product.id, ordered_qty=10)

    # Capture IDs before any commit (receive() commits internally, expiring ORM objects)
    po_id = po.id
    line_id = line.id
    tenant_id = tenant.id

    # Complete the order
    await purchase_receiving.receive(
        db,
        tenant_id=tenant_id,
        order_id=po_id,
        receipts=[{"line_id": line_id, "quantity": 10}],
    )

    await db.refresh(po)
    assert po.status == "received"
    await db.refresh(product)
    stock_after_complete = int(product.stock_quantity)
    assert stock_after_complete == 10

    # Attempt a second receive — must be blocked by status guard
    with pytest.raises(ValueError, match="recibir"):
        await purchase_receiving.receive(
            db,
            tenant_id=tenant_id,
            order_id=po_id,
            receipts=[{"line_id": line_id, "quantity": 1}],
        )

    # The ValueError left the session in a dirty state; rollback before querying
    await db.rollback()

    # Stock must not have changed
    await db.refresh(product)
    assert int(product.stock_quantity) == stock_after_complete, "stock must not change when receive is blocked"
