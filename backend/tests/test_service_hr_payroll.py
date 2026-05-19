"""Tests para app.services.hr — cálculo y persistencia de nóminas.

Cubre:
- calc_payroll: aplica SS (4.70% + 1.55% + 0.10% + 0.10%) + IRPF (configurable).
- preview_payroll: lee al empleado y devuelve el cálculo sin persistir.
- create_payroll_auto: crea Payroll con cálculo automático y persiste.

El módulo de retenciones (modelo 111) tiene su propio test
(`test_modelos_aeat_retenciones.py`); aquí nos centramos en la lógica
de cálculo de nómina del trabajador.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.db.models.hr import Employee
from app.db.models.models import Payroll
from app.services.hr.queries import calc_payroll, preview_payroll
from app.services.hr.commands import create_payroll_auto
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _seed_employee(
    db: AsyncSession,
    tenant_id,
    *,
    base_salary: Decimal | None = Decimal("2000.00"),
    irpf_rate: Decimal | None = Decimal("15.00"),
) -> Employee:
    emp = Employee(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Juan Trabajador",
        nif="12345678Z",
        base_salary=base_salary,
        irpf_rate=irpf_rate,
    )
    db.add(emp)
    await db.flush()
    return emp


# ── calc_payroll (puro) ──────────────────────────────────────────────────────


class TestCalcPayroll:
    def test_aplica_tasas_ss_estandar(self):
        # Salario 2000€, IRPF 15%
        result = calc_payroll(2000.0, 15.0)
        # SS empleado RGSS: 4.70 + 1.55 + 0.10 + 0.10 = 6.45%
        assert result["ss_contingencias_comunes"] == round(2000 * 0.0470, 2)
        assert result["ss_desempleo"] == round(2000 * 0.0155, 2)
        assert result["ss_formacion_profesional"] == round(2000 * 0.0010, 2)
        assert result["ss_mei"] == round(2000 * 0.0010, 2)
        assert result["total_ss"] == round(2000 * 0.0645, 2)

    def test_irpf_se_calcula_sobre_base(self):
        result = calc_payroll(1500.0, 20.0)
        assert result["irpf"] == round(1500 * 0.20, 2)

    def test_net_salary_es_base_menos_deducciones(self):
        result = calc_payroll(2000.0, 15.0)
        # net = base - total_ss - irpf
        expected_deductions = result["total_ss"] + result["irpf"]
        assert result["deductions"] == round(expected_deductions, 2)
        assert result["net_salary"] == round(2000.0 - expected_deductions, 2)

    def test_irpf_cero_solo_descuenta_ss(self):
        result = calc_payroll(1000.0, 0.0)
        assert result["irpf"] == 0.0
        assert result["deductions"] == result["total_ss"]
        assert result["net_salary"] == round(1000.0 - result["total_ss"], 2)

    def test_base_cero_produce_todo_cero(self):
        result = calc_payroll(0.0, 15.0)
        for k in (
            "ss_contingencias_comunes",
            "ss_desempleo",
            "ss_formacion_profesional",
            "ss_mei",
            "total_ss",
            "irpf",
            "deductions",
            "net_salary",
        ):
            assert result[k] == 0.0, f"{k} debería ser 0"


# ── preview_payroll ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestPreviewPayroll:
    async def test_devuelve_calculo_con_irpf_del_empleado(
        self, db: AsyncSession, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user
        emp = await _seed_employee(
            db, tenant.id, base_salary=Decimal("1800.00"), irpf_rate=Decimal("12.00")
        )
        await db.commit()

        preview = await preview_payroll(emp.id, tenant.id, db)

        assert preview["employee_id"] == emp.id
        assert preview["base_salary"] == 1800.0
        assert preview["irpf_rate_applied"] == 12.0
        assert preview["irpf"] == round(1800 * 0.12, 2)
        assert "net_salary" in preview

    async def test_falla_si_empleado_no_existe(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises(ValueError, match="Empleado no encontrado"):
            await preview_payroll(uuid4(), tenant.id, db)

    async def test_falla_si_empleado_no_tiene_salario_base(
        self, db, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user
        emp = await _seed_employee(db, tenant.id, base_salary=None)
        await db.commit()

        with pytest.raises(ValueError, match="salario base"):
            await preview_payroll(emp.id, tenant.id, db)


# ── create_payroll_auto ──────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCreatePayrollAuto:
    async def test_persiste_nomina_con_calculo_automatico(
        self, db, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user
        emp = await _seed_employee(
            db, tenant.id, base_salary=Decimal("2000.00"), irpf_rate=Decimal("15.00")
        )
        await db.commit()

        payload = SimpleNamespace(
            employee_id=emp.id,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            issue_date=datetime(2026, 5, 31, tzinfo=UTC),
            base_salary=None,  # → coge del empleado
            status="draft",
        )
        result = await create_payroll_auto(payload, tenant.id, db)

        assert result.id is not None
        assert float(result.base_salary) == 2000.0
        # SS comp. comunes
        assert float(result.ss_contingencias_comunes) == round(2000 * 0.0470, 2)
        # IRPF 15%
        assert float(result.irpf) == round(2000 * 0.15, 2)
        # Persistido en DB
        row = await db.execute(select(Payroll).where(Payroll.id == result.id))
        assert row.scalar_one() is not None

    async def test_usa_base_salary_del_payload_si_se_indica(
        self, db, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user
        emp = await _seed_employee(
            db, tenant.id, base_salary=Decimal("1000.00"), irpf_rate=Decimal("15.00")
        )
        await db.commit()

        payload = SimpleNamespace(
            employee_id=emp.id,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            issue_date=None,
            base_salary=2500.0,  # override
            status="draft",
        )
        result = await create_payroll_auto(payload, tenant.id, db)
        assert float(result.base_salary) == 2500.0
        assert float(result.irpf) == round(2500 * 0.15, 2)

    async def test_falla_si_base_salary_cero(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        emp = await _seed_employee(db, tenant.id, base_salary=Decimal("0.00"))
        await db.commit()

        payload = SimpleNamespace(
            employee_id=emp.id,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            issue_date=None,
            base_salary=None,
            status="draft",
        )
        with pytest.raises(ValueError, match="mayor que 0"):
            await create_payroll_auto(payload, tenant.id, db)

    async def test_falla_si_empleado_no_existe(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        payload = SimpleNamespace(
            employee_id=uuid4(),
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            issue_date=None,
            base_salary=1500.0,
            status="draft",
        )
        with pytest.raises(ValueError, match="no encontrado"):
            await create_payroll_auto(payload, tenant.id, db)
