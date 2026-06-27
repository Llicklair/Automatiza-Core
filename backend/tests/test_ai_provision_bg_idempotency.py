"""
provision_employee_bg — idempotencia de skills y guard de status.

Cubre dos arreglos en app/services/ai/employee_provisioning.py:

FIX 1 — delete-before-insert (AgentSkill):
  provision_employee_bg puede re-ejecutarse (reintento / doble-submit).
  AgentSkill NO tiene UNIQUE(employee_id, tool_module) → sin el borrado previo
  las skills se duplican en cada re-run. El fix añade:
      await session.execute(sa_delete(AgentSkill).where(...))
  antes del bucle de inserción.

FIX 2 — status guard pending_setup → idle:
  Si un admin pausa el empleado (status="paused") durante la ventana del LLM,
  el BG task NO debe sobre-escribir "paused" → "idle". El fix añade:
      if emp.status == "pending_setup": emp.status = "idle"
  mirroring el guard de la ruta sincrónica provision_employee.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from app.db.models.ai_employees import AgentSkill, AIEmployee

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_llm_resp(skills: list[str] | None = None) -> object:
    """Devuelve un objeto que simula la respuesta del LLM.

    Si no se pasan skills, la lista queda vacía pero el BG task añade siempre
    reports.create_pdf_report y reports.create_pdf_text_report → N=2 fijo.
    """
    skills_json = skills or []
    content = (
        '{"domain": "billing", "role": "Agente Test", '
        '"system_prompt": "Soy un agente de prueba.", '
        f'"skills": {skills_json!r}, '
        '"can_do": [], "cannot_do": [], "vs_others": ""}'
    )
    return type("R", (), {"content": content})()


def _make_llm_mock(skills: list[str] | None = None):
    fake_llm = AsyncMock()
    fake_llm.ainvoke = AsyncMock(return_value=_fake_llm_resp(skills))
    return fake_llm


def _make_employee(tenant_id: uuid.UUID, name: str = "Emp Test") -> AIEmployee:
    return AIEmployee(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name,
        role="Rol inicial",
        domain="custom",
        system_prompt="Prompt inicial.",
        status="pending_setup",
        is_builtin=False,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestProvisionBgIdempotency:

    @pytest.mark.asyncio
    async def test_skills_not_duplicated_on_rerun(self, db):
        """FIX 1: dos llamadas consecutivas NO duplican filas AgentSkill.

        Sin el delete-before-insert el segundo run añadiría N filas más → 2N.
        Con el fix el segundo run borra las anteriores y reinserta → N.
        """
        from app.services.ai.employee_provisioning import provision_employee_bg

        tenant_id = uuid.uuid4()
        emp = _make_employee(tenant_id)
        db.add(emp)
        await db.commit()
        emp_id = emp.id

        # Primera llamada
        with patch(
            "app.core.llm_factory.get_llm",
            return_value=_make_llm_mock(),
        ):
            await provision_employee_bg(
                employee_id=str(emp_id),
                tenant_id=str(tenant_id),
                name="Emp Test",
                role_description="Test idempotencia skills",
            )

        db.expire_all()
        res = await db.execute(
            select(func.count()).where(AgentSkill.employee_id == emp_id)
        )
        count_after_first = res.scalar_one()
        assert count_after_first >= 1, "Primera ejecución no insertó ninguna skill."

        # Segunda llamada con los mismos args
        with patch(
            "app.core.llm_factory.get_llm",
            return_value=_make_llm_mock(),
        ):
            await provision_employee_bg(
                employee_id=str(emp_id),
                tenant_id=str(tenant_id),
                name="Emp Test",
                role_description="Test idempotencia skills",
            )

        db.expire_all()
        res2 = await db.execute(
            select(func.count()).where(AgentSkill.employee_id == emp_id)
        )
        count_after_second = res2.scalar_one()

        assert count_after_second == count_after_first, (
            f"Las skills se duplicaron en el segundo run: "
            f"primer run={count_after_first}, segundo run={count_after_second}. "
            f"El delete-before-insert no está funcionando."
        )

    @pytest.mark.asyncio
    async def test_pending_setup_becomes_idle(self, db):
        """FIX 2 (happy path): pending_setup → idle tras provision_employee_bg."""
        from app.services.ai.employee_provisioning import provision_employee_bg

        tenant_id = uuid.uuid4()
        emp = _make_employee(tenant_id)
        emp.status = "pending_setup"
        db.add(emp)
        await db.commit()
        emp_id = emp.id

        with patch(
            "app.core.llm_factory.get_llm",
            return_value=_make_llm_mock(),
        ):
            await provision_employee_bg(
                employee_id=str(emp_id),
                tenant_id=str(tenant_id),
                name="Emp Test",
                role_description="Test happy path status",
            )

        db.expire_all()
        res = await db.execute(select(AIEmployee).where(AIEmployee.id == emp_id))
        refreshed = res.scalar_one()
        assert refreshed.status == "idle", (
            f"pending_setup no se convirtió en idle: status={refreshed.status!r}."
        )

    @pytest.mark.asyncio
    async def test_paused_status_not_overwritten(self, db):
        """FIX 2 (guard): un empleado 'paused' NO es sobre-escrito a 'idle'.

        Simula que un admin pausó el empleado durante la ventana del LLM.
        Sin el guard `if emp.status == 'pending_setup'` el BG task habría
        sobre-escrito silenciosamente 'paused' → 'idle'.
        """
        from app.services.ai.employee_provisioning import provision_employee_bg

        tenant_id = uuid.uuid4()
        emp = _make_employee(tenant_id)
        emp.status = "paused"  # admin ya pausó antes de que el BG task terminase
        db.add(emp)
        await db.commit()
        emp_id = emp.id

        with patch(
            "app.core.llm_factory.get_llm",
            return_value=_make_llm_mock(),
        ):
            await provision_employee_bg(
                employee_id=str(emp_id),
                tenant_id=str(tenant_id),
                name="Emp Test",
                role_description="Test guard paused",
            )

        db.expire_all()
        res = await db.execute(select(AIEmployee).where(AIEmployee.id == emp_id))
        refreshed = res.scalar_one()
        assert refreshed.status == "paused", (
            f"El BG task sobre-escribió 'paused' → '{refreshed.status}'. "
            f"El guard `if emp.status == 'pending_setup'` no está funcionando."
        )
