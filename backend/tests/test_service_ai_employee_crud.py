"""Tests para app.services.ai.employee_crud — CRUD de empleados IA (cobertura QA).

Cubre list/create/update/delete y el contrato de capacidades. No ejercita los
caminos con LLM/heartbeat (provision, instruct) que requieren servicios externos.
"""

from uuid import uuid4

import pytest

from app.services.ai.employee_crud import (
    create_employee,
    delete_employee,
    list_employees,
    update_appearance,
    update_budget,
    update_icon,
    update_status,
)


async def _make_employee(db, tenant_id):
    out, emp_id = await create_employee(
        name="Asistente Test",
        role_description="Hace tareas de prueba",
        budget_limit_usd=10.0,
        tenant_id=tenant_id,
        db=db,
        scope={"billing": ["billing.list_invoices"]},
        memory_enabled=True,
        knowledge_enabled=True,
        workflows=[],
    )
    return out, emp_id


@pytest.mark.asyncio
class TestEmployeeCrud:
    async def test_list_vacio(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        assert await list_employees(tenant.id, db) == []

    async def test_create_y_list(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        out, emp_id = await _make_employee(db, tenant.id)
        assert out["name"] == "Asistente Test"
        assert out["domain"] == "custom"
        assert out["status"] == "pending_setup"
        listed = await list_employees(tenant.id, db)
        assert len(listed) == 1
        assert listed[0]["id"] == emp_id

    async def test_create_sin_capacidades_ok(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        # 0 capacidades → un custom "fino" (solo persona) es válido: el alta NO
        # se bloquea (el contrato ≥2 capacidades se retiró el 2026-06-18).
        out, emp_id = await create_employee(
            name="Vacío",
            role_description="sin capacidades",
            budget_limit_usd=5.0,
            tenant_id=tenant.id,
            db=db,
            scope=None,
            memory_enabled=False,
            knowledge_enabled=False,
            workflows=None,
        )
        assert emp_id
        assert out["domain"] == "custom"
        assert out["memory_enabled"] is False
        assert out["knowledge_enabled"] is False

    async def test_update_icon(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        _out, emp_id = await _make_employee(db, tenant.id)
        updated = await update_icon(emp_id, tenant.id, "🤖", db)
        assert updated is not None
        assert updated["icon"] == "🤖"

    async def test_update_icon_no_existe_devuelve_none(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        assert await update_icon(str(uuid4()), tenant.id, "x", db) is None

    async def test_update_appearance(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        _out, emp_id = await _make_employee(db, tenant.id)
        updated = await update_appearance(emp_id, tenant.id, "💼", "#ff0000", db)
        assert updated["icon"] == "💼"
        assert updated["avatar_color"] == "#ff0000"

    async def test_update_status_idle_y_otro(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        _out, emp_id = await _make_employee(db, tenant.id)
        idle = await update_status(emp_id, tenant.id, "idle", db)
        assert idle["status"] == "idle"
        paused = await update_status(emp_id, tenant.id, "paused", db)
        assert paused["status"] == "paused"

    async def test_update_status_no_existe(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        assert await update_status(str(uuid4()), tenant.id, "idle", db) is None

    async def test_update_budget(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        _out, emp_id = await _make_employee(db, tenant.id)
        updated = await update_budget(emp_id, tenant.id, 99.0, db)
        assert updated["budget_limit_usd"] == 99.0
        # None desactiva el límite
        cleared = await update_budget(emp_id, tenant.id, None, db)
        assert cleared["budget_limit_usd"] is None

    async def test_delete_employee(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        _out, emp_id = await _make_employee(db, tenant.id)
        assert await delete_employee(emp_id, tenant.id, db) is True
        # Segundo intento → False (ya no existe)
        assert await delete_employee(emp_id, tenant.id, db) is False
