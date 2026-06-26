"""Regresión: endurecimiento de la recepción de pedidos de compra.

Cubre dos guards de bajo riesgo (no cambian importes, rechazan entradas inválidas):
  1. `receive()` rechaza pedidos en estado no-receptible ('received'/'cancelled');
     antes un pedido cancelado (líneas con received_quantity=0) sumaba stock
     fantasma.
  2. El schema `ReceiveLine` exige `quantity > 0`; antes 0/negativo era un no-op
     silencioso.

Control no-tautológico: un pedido en estado receptible ('draft') con qty>0 sigue
funcionando y actualiza `received_quantity`.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.receiving import ReceiveLine
from app.db.models.crm import Client
from app.db.models.orders import PurchaseOrder, PurchaseOrderLine
from app.services.sales import purchase_receiving

# ── Schema: quantity > 0 ────────────────────────────────────────────────────

@pytest.mark.parametrize("bad_qty", [0, -1, -0.01])
def test_receive_line_rejects_non_positive_quantity(bad_qty):
    with pytest.raises(ValidationError):
        ReceiveLine(line_id=uuid4(), quantity=bad_qty)


def test_receive_line_accepts_positive_quantity():
    line = ReceiveLine(line_id=uuid4(), quantity=2.5)
    assert line.quantity == 2.5


# ── Servicio: guard de estado ───────────────────────────────────────────────

async def _make_po(db, tenant, status: str) -> PurchaseOrder:
    supplier = Client(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Proveedor Test",
        client_type="supplier",
    )
    db.add(supplier)
    await db.flush()
    po = PurchaseOrder(
        id=uuid4(),
        tenant_id=tenant.id,
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
        product_id=None,  # sin producto → no toca stock/almacén
        description="Material",
        quantity=10,
        received_quantity=0,
        unit_price=0,
        total=0,
    )
    db.add(line)
    await db.flush()
    return po, line


@pytest.mark.parametrize("status", ["cancelled", "received"])
async def test_receive_rejects_non_receivable_status(db, seed_tenant_and_user, status):
    tenant, _, _ = seed_tenant_and_user
    po, line = await _make_po(db, tenant, status)

    with pytest.raises(ValueError):
        await purchase_receiving.receive(
            db,
            tenant_id=tenant.id,
            order_id=po.id,
            receipts=[{"line_id": line.id, "quantity": 5}],
        )

    # No se sumó nada: el guard corta antes de tocar stock.
    await db.refresh(line)
    assert float(line.received_quantity) == 0


async def test_receive_allows_receivable_status(db, seed_tenant_and_user):
    """Control no-tautológico: 'draft' (receptible) + qty>0 sí recibe."""
    tenant, _, _ = seed_tenant_and_user
    po, line = await _make_po(db, tenant, "draft")

    result = await purchase_receiving.receive(
        db,
        tenant_id=tenant.id,
        order_id=po.id,
        receipts=[{"line_id": line.id, "quantity": 4}],
    )

    await db.refresh(line)
    assert float(line.received_quantity) == 4
    assert result["order_id"] == str(po.id)
