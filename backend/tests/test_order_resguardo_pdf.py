"""Resguardo de depósito (PDF) de tintorería."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.db.models.crm import Client
from app.db.models.orders import SalesOrder, SalesOrderLine
from app.services.sales.order_resguardo import generate_resguardo_pdf


async def _order_with_lines(db, tenant, lines: list[tuple[str, int]]) -> SalesOrder:
    client = Client(tenant_id=tenant.id, name="María López", nif=None)
    db.add(client)
    await db.flush()
    order = SalesOrder(
        tenant_id=tenant.id,
        client_id=client.id,
        order_number="P2026-0007",
        date=datetime(2026, 5, 14, tzinfo=UTC),
        expected_delivery=datetime(2026, 5, 20, tzinfo=UTC),
        status="pending",
        amount_total=Decimal("30.00"),
    )
    db.add(order)
    await db.flush()
    for desc, qty in lines:
        db.add(
            SalesOrderLine(
                order_id=order.id,
                description=desc,
                quantity=Decimal(qty),
                unit_price=Decimal("10.00"),
                total=Decimal("10.00"),
            )
        )
    await db.commit()
    return order


@pytest.mark.asyncio
class TestResguardoPdf:
    async def test_genera_pdf_del_resguardo(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        order = await _order_with_lines(db, tenant, [("Traje de chaqueta", 1), ("Abrigo", 2)])

        pdf = await generate_resguardo_pdf(db, tenant.id, order.id)

        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000  # incluye el QR → PDF no trivial

    async def test_pedido_inexistente_lanza_lookup(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises(LookupError):
            await generate_resguardo_pdf(db, tenant.id, uuid.uuid4())
