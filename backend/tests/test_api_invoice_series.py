"""Tests de numeración correlativa de facturas (InvoiceSeries) y validación de IVA."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.db.models.models import Client, InvoiceSeries
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _invoice_payload(*, lines: list[dict]) -> dict:
    return {
        "date": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "draft",
        "invoice_type": "issued",
        "lines": lines,
    }


@pytest.mark.asyncio
async def test_invoice_auto_number_sequential(
    auth_client: AsyncClient, seed_tenant_and_user, db: AsyncSession
):
    tenant, _user, _token = seed_tenant_and_user
    cid = uuid4()
    db.add(Client(id=cid, tenant_id=tenant.id, nif="A12345678", name="Cliente Numeración"))
    await db.commit()

    y = datetime.now(UTC).year
    body = _invoice_payload(
        lines=[
            {
                "description": "Concepto A",
                "quantity": 1,
                "unit_price": 100.0,
                "tax_percentage": 21.0,
            }
        ]
    )

    r1 = await auth_client.post(f"/api/v1/clients/{cid}/invoices", json=body)
    assert r1.status_code == 201, r1.text
    assert r1.json()["invoice_number"] == f"F{y}-0001"

    r2 = await auth_client.post(f"/api/v1/clients/{cid}/invoices", json=body)
    assert r2.status_code == 201, r2.text
    assert r2.json()["invoice_number"] == f"F{y}-0002"


@pytest.mark.asyncio
async def test_invoice_invalid_vat_rejected(
    auth_client: AsyncClient, seed_tenant_and_user, db: AsyncSession
):
    tenant, _user, _token = seed_tenant_and_user
    cid = uuid4()
    db.add(Client(id=cid, tenant_id=tenant.id, nif="B87654321", name="Cliente IVA"))
    await db.commit()

    body = _invoice_payload(
        lines=[
            {
                "description": "Línea mala",
                "quantity": 1,
                "unit_price": 50.0,
                "tax_percentage": 8.0,
            }
        ]
    )
    r = await auth_client.post(f"/api/v1/clients/{cid}/invoices", json=body)
    assert r.status_code == 400
    assert "IVA" in r.json().get("detail", "")


@pytest.mark.asyncio
async def test_invoice_manual_number_does_not_consume_series_counter(
    auth_client: AsyncClient, seed_tenant_and_user, db: AsyncSession
):
    tenant, _user, _token = seed_tenant_and_user
    cid = uuid4()
    db.add(Client(id=cid, tenant_id=tenant.id, nif="C11223344", name="Cliente manual"))
    await db.commit()

    y = datetime.now(UTC).year
    manual = {
        "invoice_number": "RECT-2026-MANUAL",
        "date": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "draft",
        "invoice_type": "issued",
        "lines": [
            {
                "description": "Ajuste",
                "quantity": 1,
                "unit_price": 10.0,
                "tax_percentage": 21.0,
            }
        ],
    }
    r0 = await auth_client.post(f"/api/v1/clients/{cid}/invoices", json=manual)
    assert r0.status_code == 201
    assert r0.json()["invoice_number"] == "RECT-2026-MANUAL"

    auto = _invoice_payload(
        lines=[
            {
                "description": "Primera auto",
                "quantity": 1,
                "unit_price": 20.0,
                "tax_percentage": 21.0,
            }
        ]
    )
    r1 = await auth_client.post(f"/api/v1/clients/{cid}/invoices", json=auto)
    assert r1.status_code == 201
    assert r1.json()["invoice_number"] == f"F{y}-0001"

    row = await db.execute(
        select(InvoiceSeries).where(
            InvoiceSeries.tenant_id == tenant.id,
            InvoiceSeries.serie == "F",
            InvoiceSeries.year == y,
        )
    )
    series = row.scalar_one_or_none()
    assert series is not None
    assert series.last_number == 1
