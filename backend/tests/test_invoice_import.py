"""Tests del servicio invoice_import: factura de compra + asiento + stock seguro."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models.billing import Invoice
from app.db.models.inventory import Product
from app.db.models.models import JournalEntry
from app.services.billing.invoice_import import import_received_invoices


def _draft(apply_stock: bool, line_desc: str, qty: float = 3, unit: float = 10.0) -> dict:
    base = qty * unit
    tax = round(base * 0.21, 2)
    return {
        "emisor": {"nif": "B87654321", "name": "Proveedor Uno SL"},
        "invoice_number": "F-2026-001",
        "issue_date": "2026-05-10",
        "amount_base": base,
        "tax_amount": tax,
        "amount_total": base + tax,
        "apply_stock": apply_stock,
        "lines": [
            {"description": line_desc, "quantity": qty, "unit_price": unit,
             "tax_percentage": 21, "total": base},
        ],
    }


@pytest.mark.asyncio
async def test_import_creates_received_invoice_and_journal_entry(db, seed_tenant_and_user):
    tenant, user, _ = seed_tenant_and_user

    res = await import_received_invoices(
        db, tenant.id, [_draft(False, "Servicio sin catálogo")], user.id
    )
    assert res[0]["ok"] is True
    assert res[0]["supplier"] == "Proveedor Uno SL"

    inv = (await db.execute(select(Invoice).where(Invoice.tenant_id == tenant.id))).scalars().first()
    assert inv is not None
    assert inv.invoice_type == "received"
    assert inv.status == "draft"
    assert inv.invoice_number == "F-2026-001"

    je = (await db.execute(
        select(JournalEntry).where(JournalEntry.invoice_id == inv.id)
    )).scalars().first()
    assert je is not None  # asiento de compra generado


@pytest.mark.asyncio
async def test_import_applies_stock_for_matched_product(db, seed_tenant_and_user):
    tenant, user, _ = seed_tenant_and_user
    product = Product(
        id=uuid4(), tenant_id=tenant.id, sku="SKU1", name="Tornillo M6",
        stock_quantity=5, is_active=True,
    )
    db.add(product)
    await db.commit()

    res = await import_received_invoices(
        db, tenant.id, [_draft(True, "Tornillo M6", qty=4)], user.id
    )
    assert res[0]["ok"] is True
    assert len(res[0]["stock_applied"]) == 1
    assert res[0]["stock_applied"][0]["quantity"] == 4
    assert res[0]["stock_unmatched"] == []

    await db.refresh(product)
    assert product.stock_quantity == 9  # 5 + 4


@pytest.mark.asyncio
async def test_import_unmatched_line_does_not_touch_stock(db, seed_tenant_and_user):
    tenant, user, _ = seed_tenant_and_user
    product = Product(
        id=uuid4(), tenant_id=tenant.id, sku="SKU1", name="Tornillo M6",
        stock_quantity=5, is_active=True,
    )
    db.add(product)
    await db.commit()

    res = await import_received_invoices(
        db, tenant.id, [_draft(True, "Producto inexistente", qty=4)], user.id
    )
    assert res[0]["ok"] is True
    assert res[0]["stock_applied"] == []
    assert res[0]["stock_unmatched"] == ["Producto inexistente"]

    await db.refresh(product)
    assert product.stock_quantity == 5  # intacto


@pytest.mark.asyncio
async def test_import_without_apply_stock_skips_inventory(db, seed_tenant_and_user):
    tenant, user, _ = seed_tenant_and_user
    product = Product(
        id=uuid4(), tenant_id=tenant.id, sku="SKU1", name="Tornillo M6",
        stock_quantity=5, is_active=True,
    )
    db.add(product)
    await db.commit()

    res = await import_received_invoices(
        db, tenant.id, [_draft(False, "Tornillo M6", qty=4)], user.id
    )
    assert res[0]["ok"] is True
    assert res[0]["stock_applied"] == []

    await db.refresh(product)
    assert product.stock_quantity == 5
