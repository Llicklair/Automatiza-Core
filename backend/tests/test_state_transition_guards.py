"""Guards de transición de estado (familia `missing_state_guard`, lente L3).

Cubre tres arreglos del loop /forja sobre funciones que escribían `<obj>.status`
SIN comprobar el estado actual → re-entrada (reintento / doble-submit / cleanup
tardío) corrompía un estado avanzado:

FIX A — onboarding/regap.py `start_identification`:
  Reiniciar la identificación desde `power_granted`/`verified` regresaba el
  apoderamiento AEAT ya completado a `cert_pending`/`identifying`. Guard
  forward-only (hermano de `mark_power_granted`/`verify_regap_consulta`).

FIX B — workers/_orchestrator_state.py `_mark_task_failed`:
  El cleanup de último recurso marcaba "failed" sin mirar el estado → pisaba una
  tarea ya `done` (éxito) o `awaiting_approval` (esperando humano).

FIX C — services/orchestration/executor.py `release_employee`:
  Tras un timeout de 180s reseteaba el employee a "idle" sobre un objeto stale →
  pisaba un "paused" que un admin hubiese puesto durante la ejecución. El fix
  recarga el estado real de BD y solo pasa a "idle" si sigue "working".
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.db.models.ai_employees import AIEmployee
from app.db.models.tasks import Task


# ---------------------------------------------------------------------------
# FIX A — regap.start_identification
# ---------------------------------------------------------------------------
class TestRegapStartIdentificationGuard:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("done_status", ["power_granted", "verified"])
    async def test_cannot_restart_from_completed(self, db, done_status):
        """Reiniciar desde un estado ya completado lanza ValueError y NO regresa."""
        from app.services.onboarding.regap import (
            get_regap_status,
            start_identification,
        )

        tenant_id = uuid.uuid4()
        record = await get_regap_status(db, tenant_id=tenant_id)
        record.status = done_status
        await db.commit()

        with pytest.raises(ValueError):
            await start_identification(
                db, tenant_id=tenant_id, auth_method="cert_fnmt"
            )

        db.expire_all()
        res = await db.execute(select(type(record)).where(type(record).tenant_id == tenant_id))
        refreshed = res.scalar_one()
        assert refreshed.status == done_status, (
            f"start_identification regresó '{done_status}' → '{refreshed.status}'."
        )

    @pytest.mark.asyncio
    async def test_allows_start_from_not_started(self, db):
        """Control: el flujo normal (not_started → cert_pending) sigue funcionando."""
        from app.services.onboarding.regap import start_identification

        tenant_id = uuid.uuid4()
        record = await start_identification(
            db, tenant_id=tenant_id, auth_method="cert_fnmt"
        )
        assert record.status == "cert_pending"

    @pytest.mark.asyncio
    async def test_allows_restart_from_rejected(self, db):
        """Control: tras un rechazo el usuario PUEDE reintentar (no es estado completado)."""
        from app.services.onboarding.regap import (
            get_regap_status,
            start_identification,
        )

        tenant_id = uuid.uuid4()
        record = await get_regap_status(db, tenant_id=tenant_id)
        record.status = "rejected"
        await db.commit()

        again = await start_identification(
            db, tenant_id=tenant_id, auth_method="clave_pin"
        )
        assert again.status == "identifying"


# ---------------------------------------------------------------------------
# FIX B — _orchestrator_state._mark_task_failed
# ---------------------------------------------------------------------------
class TestMarkTaskFailedGuard:

    async def _make_task(self, db, status: str) -> uuid.UUID:
        task = Task(tenant_id=uuid.uuid4(), domain="general", status=status)
        db.add(task)
        await db.commit()
        return task.id

    @pytest.mark.asyncio
    @pytest.mark.parametrize("terminal_status", ["done", "awaiting_approval"])
    async def test_does_not_clobber(self, db, terminal_status):
        """Una tarea `done`/`awaiting_approval` NO se re-marca 'failed'."""
        from app.workers._orchestrator_state import _mark_task_failed

        task_id = await self._make_task(db, terminal_status)
        await _mark_task_failed(str(task_id), "boom")

        db.expire_all()
        res = await db.execute(select(Task).where(Task.id == task_id))
        task = res.scalar_one()
        assert task.status == terminal_status, (
            f"_mark_task_failed pisó '{terminal_status}' → '{task.status}'."
        )

    @pytest.mark.asyncio
    async def test_running_marked_failed(self, db):
        """Control: una tarea `running` SÍ se marca 'failed' con su mensaje."""
        from app.workers._orchestrator_state import _mark_task_failed

        task_id = await self._make_task(db, "running")
        await _mark_task_failed(str(task_id), "explosión interna")

        db.expire_all()
        res = await db.execute(select(Task).where(Task.id == task_id))
        task = res.scalar_one()
        assert task.status == "failed"
        assert "explosión interna" in (task.error_message or "")


# ---------------------------------------------------------------------------
# FIX C — executor.release_employee
# ---------------------------------------------------------------------------
class TestReleaseEmployeeGuard:

    def _make_employee(self, tenant_id: uuid.UUID, status: str) -> AIEmployee:
        return AIEmployee(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name="Emp Test",
            role="Rol",
            domain="custom",
            system_prompt="Prompt.",
            status=status,
            is_builtin=False,
        )

    @pytest.mark.asyncio
    async def test_paused_not_overwritten(self, db):
        """Un 'paused' (admin) NO es pisado a 'idle' por el cleanup post-timeout."""
        from app.services.orchestration.executor import release_employee

        emp = self._make_employee(uuid.uuid4(), "paused")
        db.add(emp)
        await db.commit()
        emp_id = emp.id

        # Objeto stale: el dispatch lo dejó "working" en memoria, pero BD tiene
        # "paused" porque un admin lo pausó durante los 180s.
        emp.status = "working"
        await release_employee(db, emp, label="test")

        db.expire_all()
        res = await db.execute(select(AIEmployee).where(AIEmployee.id == emp_id))
        refreshed = res.scalar_one()
        assert refreshed.status == "paused", (
            f"release_employee pisó 'paused' → '{refreshed.status}'."
        )

    @pytest.mark.asyncio
    async def test_working_becomes_idle(self, db):
        """Control: un employee 'working' SÍ vuelve a 'idle' al liberarse."""
        from app.services.orchestration.executor import release_employee

        emp = self._make_employee(uuid.uuid4(), "working")
        db.add(emp)
        await db.commit()
        emp_id = emp.id

        await release_employee(db, emp, label="test")

        db.expire_all()
        res = await db.execute(select(AIEmployee).where(AIEmployee.id == emp_id))
        refreshed = res.scalar_one()
        assert refreshed.status == "idle", (
            f"release_employee no liberó 'working' → '{refreshed.status}'."
        )
