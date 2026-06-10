"""Tool `propose_schedule` (gate hr) y export de horarios a Excel/PDF."""

from contextlib import asynccontextmanager
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.agents.hr._schedule_tools import propose_schedule
from app.db.models.hr import WorkSchedule
from app.db.models.models import Employee
from app.services.autonomy import set_policy

pytestmark = pytest.mark.asyncio


def _patched_sessions(db):
    """Patcha AsyncSessionLocal en el gate (import local) y en el body de la tool."""

    @asynccontextmanager
    async def ctx():
        yield db

    return (
        patch("app.db.base.AsyncSessionLocal", side_effect=ctx),
        patch("app.agents.hr._schedule_tools.AsyncSessionLocal", side_effect=ctx),
    )


async def _seed_employee(db, tenant_id, name="Ana López"):
    emp = Employee(id=uuid4(), tenant_id=tenant_id, name=name, status="active")
    db.add(emp)
    await db.commit()
    return emp


def _days():
    return [
        {"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"},
        {"day_of_week": 1, "start_time": "09:00", "end_time": "17:00"},
    ]


async def test_propose_schedule_auto_aplica(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_employee(db, tenant.id)
    await set_policy(db, tenant_id=tenant.id, domain="hr", mode="AUTO")
    await db.commit()

    p1, p2 = _patched_sessions(db)
    with p1, p2:
        result = await propose_schedule.coroutine(
            tenant_id=str(tenant.id),
            schedules=[{"employee_id": str(emp.id), "days": _days()}],
            rationale="Cobertura semanal",
        )

    assert "Horario aplicado" in result
    rows = (
        await db.execute(select(WorkSchedule).where(WorkSchedule.employee_id == emp.id))
    ).scalars().all()
    assert len(rows) == 2
    assert {r.day_of_week for r in rows} == {0, 1}


async def test_propose_schedule_confirm_por_defecto_no_aplica(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_employee(db, tenant.id)

    p1, p2 = _patched_sessions(db)
    with p1, p2:
        result = await propose_schedule.coroutine(
            tenant_id=str(tenant.id),
            schedules=[{"employee_id": str(emp.id), "days": _days()}],
        )

    assert "Horario aplicado" not in result  # queda pendiente de aprobación
    rows = (
        await db.execute(select(WorkSchedule).where(WorkSchedule.employee_id == emp.id))
    ).scalars().all()
    assert rows == []


async def test_propose_schedule_validaciones(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    await set_policy(db, tenant_id=tenant.id, domain="hr", mode="AUTO")
    await db.commit()

    p1, p2 = _patched_sessions(db)
    with p1, p2:
        out_empty = await propose_schedule.coroutine(tenant_id=str(tenant.id), schedules=[])
        out_bad_day = await propose_schedule.coroutine(
            tenant_id=str(tenant.id),
            schedules=[{"employee_id": str(uuid4()), "days": [
                {"day_of_week": 9, "start_time": "09:00", "end_time": "17:00"}
            ]}],
        )
        out_missing = await propose_schedule.coroutine(
            tenant_id=str(tenant.id),
            schedules=[{"employee_id": str(uuid4()), "days": _days()}],
        )

    assert "vacía" in out_empty
    assert "day_of_week inválido" in out_bad_day
    assert "no encontrados" in out_missing


async def test_export_schedules_endpoint(db, auth_client, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_employee(db, tenant.id, name="Luis Pérez")
    db.add(WorkSchedule(
        tenant_id=tenant.id, employee_id=emp.id,
        day_of_week=0, start_time="08:00", end_time="16:00", active=True,
    ))
    await db.commit()

    r = await auth_client.get("/api/v1/hr/schedules/export?format=xlsx")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert r.content[:2] == b"PK"  # zip/xlsx magic

    r = await auth_client.get("/api/v1/hr/schedules/export?format=pdf")
    assert r.status_code == 200

    r = await auth_client.get("/api/v1/hr/schedules/export?format=csv")
    assert r.status_code == 422
