"""Etiquetas de prenda/pedido (PDF) para tintorería."""
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.db.models.crm import Client
from app.db.models.orders import SalesOrder, SalesOrderLine
from app.services.sales.order_labels import generate_order_labels_pdf


async def _order_with_lines(db, tenant, lines: list[tuple[str, int]]) -> SalesOrder:
    client = Client(tenant_id=tenant.id, name="María López", nif=None)
    db.add(client)
    await db.flush()
    order = SalesOrder(
        tenant_id=tenant.id,
        client_id=client.id,
        order_number="P2026-0001",
        date=datetime(2026, 5, 14, tzinfo=UTC),
        expected_delivery=datetime(2026, 5, 20, tzinfo=UTC),
        status="pending",
    )
    db.add(order)
    await db.flush()
    for desc, qty in lines:
        db.add(
            SalesOrderLine(
                order_id=order.id,
                description=desc,
                quantity=Decimal(qty),
                unit_price=Decimal("5.00"),
                total=Decimal("5.00"),
            )
        )
    await db.commit()
    return order


@pytest.mark.asyncio
class TestOrderLabelsPdf:
    async def test_genera_pdf_una_etiqueta_por_prenda(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        order = await _order_with_lines(db, tenant, [("Camisa blanca", 2), ("Pantalón", 1)])

        pdf = await generate_order_labels_pdf(db, tenant.id, order.id)

        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 800  # 3 etiquetas → PDF no trivial

    async def test_pedido_inexistente_lanza_lookup(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises(LookupError):
            await generate_order_labels_pdf(db, tenant.id, uuid.uuid4())

    async def test_pedido_sin_prendas_lanza_valueerror(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        order = await _order_with_lines(db, tenant, [])
        with pytest.raises(ValueError):
            await generate_order_labels_pdf(db, tenant.id, order.id)
