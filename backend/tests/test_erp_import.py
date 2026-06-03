"""Tests del servicio erp_import: Excel/CSV → entidades del ERP (preview + commit)."""

import os
import tempfile
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.models.crm import Client
from app.db.models.inventory import Product
from app.db.models.tenant import TenantDocument
from app.services.documents.erp_import import apply_import, preview_import


async def _make_doc(db, tenant_id, csv_text: str, name: str = "datos.csv") -> TenantDocument:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(csv_text)
    doc = TenantDocument(
        id=uuid4(), tenant_id=tenant_id, file_name=name, file_path=path,
        file_type="text/csv", file_size=len(csv_text), category="excels", status="uploaded",
    )
    db.add(doc)
    await db.commit()
    return doc


PRODUCTS_CSV = "nombre,sku,precio,iva,stock\nTornillo M6,SKU1,0.50,21,100\nTuerca M6,SKU2,0.30,21,200\n,SKU3,1.00,21,5\n"


@pytest.mark.asyncio
async def test_preview_detects_products_and_counts(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    doc = await _make_doc(db, tenant.id, PRODUCTS_CSV)

    pv = await preview_import(db, tenant.id, doc.id, None)
    assert pv["target"] == "productos"
    assert pv["total_rows"] == 3
    assert pv["importable"] == 2  # la fila sin nombre se omite
    assert "name" in pv["mapped_fields"] and "price" in pv["mapped_fields"]


@pytest.mark.asyncio
async def test_apply_creates_products_with_coerced_numbers(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    doc = await _make_doc(db, tenant.id, PRODUCTS_CSV)

    res = await apply_import(db, tenant.id, doc.id, "productos")
    assert res["created"] == 2
    assert res["skipped"] == 1

    prods = (await db.execute(select(Product).where(Product.tenant_id == tenant.id))).scalars().all()
    assert len(prods) == 2
    by_sku = {p.sku: p for p in prods}
    assert float(by_sku["SKU1"].price) == 0.5
    assert int(by_sku["SKU1"].stock_quantity) == 100


@pytest.mark.asyncio
async def test_apply_clients_target_override(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    csv = "nombre,nif,email\nAcme SL,B11111111,a@acme.com\nBeta SL,B22222222,b@beta.com\n"
    doc = await _make_doc(db, tenant.id, csv)

    res = await apply_import(db, tenant.id, doc.id, "clientes")
    assert res["created"] == 2
    count = (await db.execute(
        select(func.count()).select_from(Client).where(Client.tenant_id == tenant.id)
    )).scalar()
    assert count == 2


@pytest.mark.asyncio
async def test_preview_missing_document_raises(db, seed_tenant_and_user):
    tenant, _, _ = seed_tenant_and_user
    with pytest.raises(LookupError):
        await preview_import(db, tenant.id, uuid4(), None)
