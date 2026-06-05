"""Migración de nóminas históricas (import desde otro programa).

Migración ≠ generación: se preservan los importes del sistema de origen y la
operación es idempotente por (empleado, período), de modo que reejecutar la
migración no duplica el histórico.
"""

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.hr import Employee, Payroll
from app.db.models.models import Tenant
from app.services.migration.bulk_import import import_payrolls_rows


async def _seed(db: AsyncSession):
    tenant = Tenant(id=uuid4(), name="Mig Corp S.L.", nif="B33445566", plan="starter")
    db.add(tenant)
    await db.flush()
    emp = Employee(id=uuid4(), tenant_id=tenant.id, name="Ana Pérez", nif="12345678Z", base_salary=2000)
    db.add(emp)
    await db.flush()
    return tenant, emp


def _row(periodo="2026-01", neto="1650.50", **over):
    base = {
        "nif": "12345678Z",
        "periodo": periodo,
        "salario_base": "2000",
        "bruto": "2000",
        "irpf": "300",
        "deducciones": "350",
        "liquido": neto,
    }
    base.update(over)
    return base


async def _count(db, tenant_id) -> int:
    r = await db.execute(select(func.count(Payroll.id)).where(Payroll.tenant_id == tenant_id))
    return int(r.scalar() or 0)


class TestPayrollMigration:
    @pytest.mark.asyncio
    async def test_importa_y_preserva_importes(self, db: AsyncSession):
        tenant, emp = await _seed(db)
        res = await import_payrolls_rows([_row()], tenant.id, db)
        assert res.created == 1
        r = await db.execute(select(Payroll).where(Payroll.tenant_id == tenant.id))
        p = r.scalars().first()
        # Se respetan los importes del programa de origen (no se recalcula).
        assert float(p.base_salary) == 2000.0
        assert float(p.net_salary) == 1650.50
        assert float(p.irpf) == 300.0
        assert p.employee_id == emp.id
        assert p.status == "paid"  # histórica

    @pytest.mark.asyncio
    async def test_idempotente_no_duplica(self, db: AsyncSession):
        tenant, _ = await _seed(db)
        await import_payrolls_rows([_row()], tenant.id, db)
        res2 = await import_payrolls_rows([_row()], tenant.id, db)  # reejecutar migración
        assert res2.created == 0
        assert res2.skipped == 1
        assert await _count(db, tenant.id) == 1

    @pytest.mark.asyncio
    async def test_distinto_periodo_si_crea(self, db: AsyncSession):
        tenant, _ = await _seed(db)
        await import_payrolls_rows([_row("2026-01")], tenant.id, db)
        await import_payrolls_rows([_row("2026-02")], tenant.id, db)
        assert await _count(db, tenant.id) == 2

    @pytest.mark.asyncio
    async def test_empleado_inexistente_error(self, db: AsyncSession):
        tenant, _ = await _seed(db)
        res = await import_payrolls_rows([_row(nif="99999999R")], tenant.id, db)
        assert res.created == 0
        assert res.skipped == 1
        assert res.errors and "no encontrado" in res.errors[0]["reason"].lower()

    @pytest.mark.asyncio
    async def test_falta_importe_obligatorio_error(self, db: AsyncSession):
        tenant, _ = await _seed(db)
        res = await import_payrolls_rows([_row(liquido="")], tenant.id, db)
        assert res.created == 0
        assert res.errors
