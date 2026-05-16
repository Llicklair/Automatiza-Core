"""Tests para los Modelos AEAT 111 (trimestral) y 190 (anual) — MOD.111/MOD.190."""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.db.models.hr import Employee, Payroll
from app.services.reports.modelos_aeat import (
    build_modelo_111_data,
    build_modelo_190_data,
)


def _employee(tenant_id, *, name: str, nif: str) -> Employee:
    return Employee(tenant_id=tenant_id, name=name, nif=nif)


def _payroll(
    tenant_id, employee_id, *,
    period_start: datetime,
    base_salary: Decimal = Decimal("1500.00"),
    base_irpf: Decimal = Decimal("1500.00"),
    irpf: Decimal = Decimal("225.00"),
) -> Payroll:
    return Payroll(
        tenant_id=tenant_id,
        employee_id=employee_id,
        period_start=period_start,
        period_end=period_start,
        issue_date=period_start,
        base_salary=base_salary,
        net_salary=base_salary - irpf,
        base_irpf=base_irpf,
        irpf=irpf,
    )


@pytest.mark.asyncio
class TestModelo111:
    async def test_suma_retenciones_trimestrales(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        emp = _employee(tenant.id, name="Juan Perez", nif="12345678A")
        db.add(emp)
        await db.flush()

        # 3 nóminas en 1T 2026 (enero, febrero, marzo)
        for month in (1, 2, 3):
            db.add(_payroll(
                tenant.id, emp.id,
                period_start=datetime(2026, month, 1, tzinfo=UTC),
                base_irpf=Decimal("1500.00"),
                irpf=Decimal("225.00"),
            ))
        await db.commit()

        result = await build_modelo_111_data(db, tenant.id, quarter=1, year=2026)
        assert result["modelo"] == "111"
        assert result["periodo"] == "1T"
        assert result["num_perceptores"] == 1
        assert result["total_base_retenciones"] == 4500.00  # 3 × 1500
        assert result["total_retencion_practicada"] == 675.00  # 3 × 225
        perceptor = result["perceptores_trabajo_personal"][0]
        assert perceptor["nombre"] == "Juan Perez"
        assert perceptor["nif"] == "12345678A"
        assert perceptor["num_nominas"] == 3

    async def test_solo_nominas_del_trimestre(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        emp = _employee(tenant.id, name="Ana Lopez", nif="87654321B")
        db.add(emp)
        await db.flush()

        # 1 nómina en 1T y 1 en 2T → solo 1T debe aparecer en 1T 2026
        db.add(_payroll(tenant.id, emp.id, period_start=datetime(2026, 2, 1, tzinfo=UTC)))
        db.add(_payroll(tenant.id, emp.id, period_start=datetime(2026, 5, 1, tzinfo=UTC)))
        await db.commit()

        result_q1 = await build_modelo_111_data(db, tenant.id, quarter=1, year=2026)
        result_q2 = await build_modelo_111_data(db, tenant.id, quarter=2, year=2026)
        assert result_q1["perceptores_trabajo_personal"][0]["num_nominas"] == 1
        assert result_q2["perceptores_trabajo_personal"][0]["num_nominas"] == 1

    async def test_agrupa_por_empleado(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        e1 = _employee(tenant.id, name="Empleado 1", nif="11111111A")
        e2 = _employee(tenant.id, name="Empleado 2", nif="22222222B")
        db.add_all([e1, e2])
        await db.flush()
        for emp_id in (e1.id, e2.id):
            db.add(_payroll(tenant.id, emp_id, period_start=datetime(2026, 2, 1, tzinfo=UTC)))
            db.add(_payroll(tenant.id, emp_id, period_start=datetime(2026, 3, 1, tzinfo=UTC)))
        await db.commit()

        result = await build_modelo_111_data(db, tenant.id, quarter=1, year=2026)
        assert result["num_perceptores"] == 2
        # Cada empleado tiene 2 nóminas
        for perceptor in result["perceptores_trabajo_personal"]:
            assert perceptor["num_nominas"] == 2

    async def test_quarter_invalido_raises(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        with pytest.raises(ValueError):
            await build_modelo_111_data(db, tenant.id, quarter=0, year=2026)

    async def test_sin_nominas_devuelve_vacio(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        result = await build_modelo_111_data(db, tenant.id, quarter=1, year=2026)
        assert result["num_perceptores"] == 0
        assert result["total_retencion_practicada"] == 0


@pytest.mark.asyncio
class TestModelo190:
    async def test_consolida_anualmente(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        emp = _employee(tenant.id, name="Anual", nif="00000000Z")
        db.add(emp)
        await db.flush()

        # 12 nóminas (una por mes)
        for month in range(1, 13):
            db.add(_payroll(
                tenant.id, emp.id,
                period_start=datetime(2026, month, 1, tzinfo=UTC),
                base_irpf=Decimal("2000.00"),
                irpf=Decimal("300.00"),
            ))
        await db.commit()

        result = await build_modelo_190_data(db, tenant.id, year=2026)
        assert result["modelo"] == "190"
        assert result["ejercicio"] == 2026
        assert result["num_perceptores"] == 1
        assert result["total_percepcion_integra"] == 24000.00  # 12 × 2000
        assert result["total_retencion_practicada"] == 3600.00  # 12 × 300
        p = result["perceptores"][0]
        assert p["clave_percepcion"] == "A"
        assert p["num_nominas"] == 12

    async def test_solo_nominas_del_year(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        emp = _employee(tenant.id, name="Cross-year", nif="99999999Z")
        db.add(emp)
        await db.flush()

        db.add(_payroll(tenant.id, emp.id, period_start=datetime(2025, 12, 1, tzinfo=UTC)))
        db.add(_payroll(tenant.id, emp.id, period_start=datetime(2026, 1, 1, tzinfo=UTC)))
        db.add(_payroll(tenant.id, emp.id, period_start=datetime(2027, 1, 1, tzinfo=UTC)))
        await db.commit()

        result_2026 = await build_modelo_190_data(db, tenant.id, year=2026)
        assert result_2026["perceptores"][0]["num_nominas"] == 1
