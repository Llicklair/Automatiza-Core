"""Filtros de correctitud de los checks de alertas.

Cubre dos bugs:
  A) low-stock debe ignorar productos dados de baja (is_active=False).
  B) overdue/due_soon NO deben disparar sobre borradores (status="draft"); solo
     sobre facturas emitidas-impagadas ("pending"/"sent").
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.db.models.inventory import Product
from app.services.alerts.service import (
    _check_due_soon_invoices,
    _check_low_stock,
    _check_overdue_invoices,
)


def _make_product(tenant_id, *, name, is_active):
    return Product(
        id=uuid4(),
        tenant_id=tenant_id,
        name=name,
        is_active=is_active,
        stock_quantity=1,
        stock_min_alert=10,  # stock(1) <= min(10) → condición de stock bajo
    )


def _make_invoice(tenant_id, client_id, *, status, due_date):
    return Invoice(
        id=uuid4(),
        tenant_id=tenant_id,
        client_id=client_id,
        date=datetime.now(UTC),
        due_date=due_date,
        amount_total=100,
        status=status,
        invoice_type="issued",
    )


@pytest.mark.asyncio
async def test_low_stock_skips_inactive_product(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user

    db.add(_make_product(tenant.id, name="Activo bajo", is_active=True))
    db.add(_make_product(tenant.id, name="Baja bajo", is_active=False))
    await db.commit()

    alerts = await _check_low_stock(db, tenant.id)
    labels = {a["label"] for a in alerts}

    # CONTROL: el producto activo SÍ alerta.
    assert any("Activo bajo" in lbl for lbl in labels), labels
    # BUG A: el producto inactivo NO debe alertar.
    assert not any("Baja bajo" in lbl for lbl in labels), labels


@pytest.mark.asyncio
async def test_overdue_skips_draft_invoices(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    client = Client(id=uuid4(), tenant_id=tenant.id, name="Cliente Test")
    db.add(client)
    await db.flush()

    past = datetime.now(UTC) - timedelta(days=5)
    inv_draft = _make_invoice(tenant.id, client.id, status="draft", due_date=past)
    inv_pending = _make_invoice(tenant.id, client.id, status="pending", due_date=past)
    inv_sent = _make_invoice(tenant.id, client.id, status="sent", due_date=past)
    db.add_all([inv_draft, inv_pending, inv_sent])
    await db.commit()

    alerts = await _check_overdue_invoices(db, tenant.id)
    overdue_ids = {a["entity_id"] for a in alerts}

    # CONTROL: emitidas-impagadas (pending/sent) SÍ vencen.
    assert str(inv_pending.id) in overdue_ids, overdue_ids
    assert str(inv_sent.id) in overdue_ids, overdue_ids
    # BUG B: el borrador NO debe contar como vencido.
    assert str(inv_draft.id) not in overdue_ids, overdue_ids


@pytest.mark.asyncio
async def test_due_soon_skips_draft_invoices(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    client = Client(id=uuid4(), tenant_id=tenant.id, name="Cliente Test")
    db.add(client)
    await db.flush()

    soon = datetime.now(UTC) + timedelta(days=2)
    inv_draft = _make_invoice(tenant.id, client.id, status="draft", due_date=soon)
    inv_pending = _make_invoice(tenant.id, client.id, status="pending", due_date=soon)
    db.add_all([inv_draft, inv_pending])
    await db.commit()

    alerts = await _check_due_soon_invoices(db, tenant.id)
    due_soon_ids = {a["entity_id"] for a in alerts}

    # CONTROL: pending próxima a vencer SÍ alerta.
    assert str(inv_pending.id) in due_soon_ids, due_soon_ids
    # BUG B: el borrador NO debe alertar.
    assert str(inv_draft.id) not in due_soon_ids, due_soon_ids
