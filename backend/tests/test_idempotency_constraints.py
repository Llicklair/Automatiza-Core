"""UNIQUE de idempotencia (migración 0067): la BD rechaza dobles inserciones que
los guards check-then-act (TOCTOU) dejaban pasar bajo concurrencia.

- payrolls: una nómina por (tenant, empleado, period_start).
- tenant_integrations: una integración por (tenant, tipo).
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models.auth import Tenant
from app.db.models.hr import Employee, Payroll
from app.db.models.tenant import TenantIntegration


@pytest.mark.asyncio
async def test_tenant_integration_unique_por_tipo(db):
    """Dos integraciones del mismo tipo para el mismo tenant → IntegrityError.
    Antes, dos connect_telegram concurrentes creaban filas duplicadas."""
    tenant = Tenant(id=uuid4(), name="T Int", nif="B40000000", plan="starter")
    db.add(tenant)
    await db.flush()

    db.add(TenantIntegration(tenant_id=tenant.id, integration_type="telegram"))
    await db.commit()

    db.add(TenantIntegration(tenant_id=tenant.id, integration_type="telegram"))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


@pytest.mark.asyncio
async def test_payroll_unique_por_periodo(db):
    """Dos nóminas para el mismo (tenant, empleado, period_start) → IntegrityError.
    Activa el handler `except IntegrityError` que ya existía en generate_all_payrolls."""
    tenant = Tenant(id=uuid4(), name="T Pay", nif="B50000000", plan="starter")
    db.add(tenant)
    await db.flush()
    emp = Employee(id=uuid4(), tenant_id=tenant.id, name="Empleado X")
    db.add(emp)
    await db.flush()

    period_start = datetime(2026, 6, 1, tzinfo=UTC)

    def _mk() -> Payroll:
        return Payroll(
            tenant_id=tenant.id,
            employee_id=emp.id,
            period_start=period_start,
            period_end=datetime(2026, 6, 30, tzinfo=UTC),
            issue_date=datetime.now(UTC),
            base_salary=Decimal("2000.00"),
            net_salary=Decimal("1600.00"),
        )

    db.add(_mk())
    await db.commit()

    db.add(_mk())
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()
