"""Repro /forja: update_payroll ignora la jornada parcial al recalcular.

Hallazgo: `_payroll.update_payroll` recalcula con `calc_payroll(base, irpf)`
usando los kwargs por defecto (jornada 100% / 12 pagas / sin baja IT), mientras
que `create_payroll_auto` -> `calc_payroll_for_employee` SÍ deriva `jornada_pct`
desde la ficha del empleado. Editar la base de un empleado a media jornada
recalcula como jornada completa -> el neto se DUPLICA.

Este test fija el comportamiento CORRECTO (el neto tras editar debe seguir
reflejando la media jornada) y se marca xfail mientras el bug exista.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.db.models.hr import Employee
from app.services.hr.commands import create_payroll_auto, update_payroll
from sqlalchemy.ext.asyncio import AsyncSession


async def _seed_part_time_employee(db: AsyncSession, tenant_id) -> Employee:
    """Empleado a MEDIA jornada: 20h/40h = jornada_pct 50%."""
    emp = Employee(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Ana MediaJornada",
        nif="12345678Z",
        base_salary=Decimal("2000.00"),
        irpf_rate=Decimal("15.00"),
        jornada_tipo="parcial",
        jornada_horas_semana=Decimal("20.0"),
        num_pagas=12,
    )
    db.add(emp)
    await db.flush()
    return emp


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="BUG: update_payroll ignora jornada_pct/num_pagas/dias_baja_it al "
    "recalcular -> neto incorrecto al editar (hallazgo /forja)",
    strict=False,
)
async def test_update_payroll_respeta_media_jornada(db: AsyncSession, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_part_time_employee(db, tenant.id)
    await db.commit()

    # 1) Camino normal: create_payroll_auto deriva jornada parcial.
    payload = SimpleNamespace(
        employee_id=emp.id,
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
        issue_date=datetime(2026, 5, 31, tzinfo=UTC),
        base_salary=None,  # coge la del empleado (2000) y la prorratea al 50%
        status="draft",
    )
    created = await create_payroll_auto(payload, tenant.id, db)
    net_correcto = float(created.net_salary)

    # Sanidad: media jornada sobre base 2000 => devengo ~1000, neto < 1000.
    assert float(created.gross_salary) == pytest.approx(1000.0, abs=1.0), (
        f"create_payroll_auto debería prorratear al 50%: gross={created.gross_salary}"
    )
    assert net_correcto < 1000.0

    # 2) Editar disparando el recálculo: re-set de base_salary (mismo valor).
    update_payload = SimpleNamespace(model_dump=lambda **k: {"base_salary": 2000.0})
    updated = await update_payroll(created.id, update_payload, tenant.id, db)
    net_tras_editar = float(updated.net_salary)

    # 3) CORRECTO: el neto tras editar debe seguir reflejando media jornada,
    #    no duplicarse por recalcular como jornada completa.
    assert net_tras_editar == pytest.approx(net_correcto, abs=1.0), (
        f"update_payroll duplica el neto: correcto={net_correcto:.2f} "
        f"vs tras-editar={net_tras_editar:.2f}"
    )
