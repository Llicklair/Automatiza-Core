"""Tests de API: libro registro AEAT (CSV) y nómina determinista (preview + auto)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Client, Employee, Invoice, InvoiceLine, Tenant


@pytest.mark.asyncio
async def test_libro_registro_emitidas_csv(auth_client: AsyncClient, seed_tenant_and_user, db: AsyncSession):
    tenant, _user, _token = seed_tenant_and_user
    cid = uuid4()
    db.add(Client(id=cid, tenant_id=tenant.id, nif="A87654321", name="Cliente SA"))
    inv_id = uuid4()
    db.add(
        Invoice(
            id=inv_id,
            tenant_id=tenant.id,
            client_id=cid,
            invoice_number="F2026-0042",
            date=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
            amount_base=Decimal("100.00"),
            tax_amount=Decimal("21.00"),
            amount_total=Decimal("121.00"),
            status="paid",
            invoice_type="issued",
        )
    )
    db.add(
        InvoiceLine(
            invoice_id=inv_id,
            description="Servicio test",
            quantity=Decimal("1"),
            unit_price=Decimal("100"),
            tax_percentage=Decimal("21"),
            total=Decimal("121"),
        )
    )
    await db.commit()

    r = await auth_client.get("/api/v1/reports/libro-registro", params={"year": 2026, "type": "emitidas"})
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    body = r.text
    assert "Nº Factura" in body
    assert "F2026-0042" in body
    assert "A87654321" in body
    assert "Cliente SA" in body


@pytest.mark.asyncio
async def test_libro_registro_recibidas_filters_type(
    auth_client: AsyncClient, seed_tenant_and_user, db: AsyncSession
):
    tenant, _u, _t = seed_tenant_and_user
    cid = uuid4()
    db.add(Client(id=cid, tenant_id=tenant.id, nif="B11222333", name="Proveedor SL"))
    inv_id = uuid4()
    db.add(
        Invoice(
            id=inv_id,
            tenant_id=tenant.id,
            client_id=cid,
            invoice_number="R-99",
            date=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
            amount_base=Decimal("200.00"),
            tax_amount=Decimal("42.00"),
            amount_total=Decimal("242.00"),
            status="paid",
            invoice_type="received",
        )
    )
    await db.commit()

    r_emit = await auth_client.get("/api/v1/reports/libro-registro", params={"year": 2026, "type": "emitidas"})
    assert r_emit.status_code == 200
    assert "R-99" not in r_emit.text

    r_rec = await auth_client.get("/api/v1/reports/libro-registro", params={"year": 2026, "type": "recibidas"})
    assert r_rec.status_code == 200
    assert "R-99" in r_rec.text
    assert "B11222333" in r_rec.text


@pytest.mark.asyncio
async def test_libro_registro_empty_year_has_header(auth_client: AsyncClient, seed_tenant_and_user):
    r = await auth_client.get("/api/v1/reports/libro-registro", params={"year": 2026, "type": "emitidas"})
    assert r.status_code == 200
    lines = [ln for ln in r.text.strip().splitlines() if ln.strip()]
    assert len(lines) == 1
    assert lines[0].startswith("Nº Factura")


@pytest.mark.asyncio
async def test_payroll_preview_requires_base_salary(auth_client: AsyncClient, seed_tenant_and_user, db: AsyncSession):
    tenant, _u, _t = seed_tenant_and_user
    emp_id = uuid4()
    db.add(
        Employee(
            id=emp_id,
            tenant_id=tenant.id,
            name="Sin salario",
            status="active",
            base_salary=None,
        )
    )
    await db.commit()

    r = await auth_client.get(f"/api/v1/hr/employees/{emp_id}/payroll/preview")
    assert r.status_code == 400
    detail = r.json().get("detail", "")
    msg = detail if isinstance(detail, str) else str(detail)
    assert "salario" in msg.lower()


@pytest.mark.asyncio
async def test_payroll_preview_and_auto_match(auth_client: AsyncClient, seed_tenant_and_user, db: AsyncSession):
    tenant, _u, _t = seed_tenant_and_user
    emp_id = uuid4()
    db.add(
        Employee(
            id=emp_id,
            tenant_id=tenant.id,
            name="Ana Test",
            status="active",
            base_salary=Decimal("3000.00"),
            irpf_rate=Decimal("15.00"),
        )
    )
    await db.commit()

    prev = await auth_client.get(f"/api/v1/hr/employees/{emp_id}/payroll/preview")
    assert prev.status_code == 200
    p = prev.json()
    assert p["base_salary"] == 3000.0
    assert p["irpf_rate_applied"] == 15.0
    assert p["net_salary"] < 3000.0
    assert p["deductions"] == pytest.approx(float(p["total_ss"]) + float(p["irpf"]), rel=1e-9)

    payload = {
        "employee_id": str(emp_id),
        "period_start": "2026-04-01T00:00:00",
        "period_end": "2026-04-30T23:59:59",
        "issue_date": "2026-04-28T00:00:00",
        "status": "draft",
    }
    cr = await auth_client.post("/api/v1/hr/payrolls/auto", json=payload)
    assert cr.status_code == 201
    row = cr.json()
    assert row["status"] == "draft"
    assert row["base_salary"] == pytest.approx(p["base_salary"])
    assert row["net_salary"] == pytest.approx(p["net_salary"])
    assert row["deductions"] == pytest.approx(p["deductions"])


@pytest.mark.asyncio
async def test_payroll_auto_rejects_other_tenant_employee(
    auth_client: AsyncClient, seed_tenant_and_user, db: AsyncSession
):
    """Empleado de otro tenant no debe poder usarse desde el token actual."""
    tenant_a, _ua, _ta = seed_tenant_and_user
    tenant_b = Tenant(
        id=uuid4(),
        name="Otra SL",
        nif="B99999999",
        plan="starter",
    )
    db.add(tenant_b)
    await db.flush()
    emp_b = Employee(
        id=uuid4(),
        tenant_id=tenant_b.id,
        name="Externo",
        status="active",
        base_salary=Decimal("2000.00"),
    )
    db.add(emp_b)
    await db.commit()

    payload = {
        "employee_id": str(emp_b.id),
        "period_start": "2026-05-01T00:00:00",
        "period_end": "2026-05-31T00:00:00",
        "status": "draft",
    }
    r = await auth_client.post("/api/v1/hr/payrolls/auto", json=payload)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_payroll_preview_404_unknown_employee(auth_client: AsyncClient, seed_tenant_and_user):
    fake = uuid4()
    r = await auth_client.get(f"/api/v1/hr/employees/{fake}/payroll/preview")
    assert r.status_code == 404
