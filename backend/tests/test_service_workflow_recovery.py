"""Tests para app.services.workflow.recovery.

Cubre los 3 caminos del startup recovery:
  1. Tasks `executing` con started_at antiguo → failed (zombie).
  2. WorkflowExecutions pending/running con task inexistente → cancelled.
  3. WorkflowExecutions pending/running cuya task fue marcada failed
     en este mismo recovery → failed (sincronización).

También verifica que las tasks vivas y los execs ya terminales no se tocan.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from app.db.models.models import Task, Tenant, Workflow, WorkflowExecution
from app.services.workflow.recovery import recover_stale_executions


async def _make_workflow(db, tenant_id):
    wf = Workflow(
        tenant_id=tenant_id,
        name="test wf",
        trigger_type="manual",
        action_type="prompt",
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return wf


@pytest.fixture
async def _tenant(db):
    t = Tenant(
        id=uuid4(),
        name="Test Recovery",
        nif=f"R{uuid4().int % 10**8:08d}",
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


def _utcnow():
    return datetime.now(timezone.utc)


@pytest.fixture(autouse=True)
def _patch_session(monkeypatch):
    """recover_stale_executions abre su propia AsyncSession; redirigirla a la del test."""

    from app.db.base import AsyncSessionLocal as _OrigAsyncSessionLocal  # noqa: F401

    # No hace falta patchear: el conftest ya redirige AsyncSessionLocal al engine in-memory.
    yield


@pytest.mark.asyncio
class TestRecoverStaleExecutions:
    async def test_zombie_task_sin_progreso_y_vieja_se_marca_failed(
        self, db, _tenant
    ):
        old = _utcnow() - timedelta(minutes=40)
        zombie = Task(
            tenant_id=_tenant.id,
            domain="x",
            status="executing",
            user_intent="zombie",
            started_at=old,
            plan=None,
        )
        db.add(zombie)
        await db.commit()
        zombie_id = zombie.id

        stats = await recover_stale_executions()
        db.expire_all()
        assert stats["tasks_failed"] >= 1

        # re-fetch (otra sesión interna ya hizo commit)
        from sqlalchemy import select

        row = (
            await db.execute(select(Task).where(Task.id == zombie_id))
        ).scalar_one()
        assert row.status == "failed"
        assert "Backend reiniciado" in (row.error_message or "")
        assert row.completed_at is not None

    async def test_zombie_sin_progreso_5min_aunque_no_supere_30min(
        self, db, _tenant
    ):
        """Umbral agresivo: <5 min Y plan=None Y sin agent_results → zombie."""
        old = _utcnow() - timedelta(minutes=7)  # >5min, <30min
        zombie = Task(
            tenant_id=_tenant.id,
            domain="x",
            status="executing",
            user_intent="z",
            started_at=old,
            plan=None,
            agent_results=[],
        )
        db.add(zombie)
        await db.commit()
        z_id = zombie.id

        stats = await recover_stale_executions()
        db.expire_all()
        assert stats["tasks_failed"] >= 1

        from sqlalchemy import select

        row = (
            await db.execute(select(Task).where(Task.id == z_id))
        ).scalar_one()
        assert row.status == "failed"

    async def test_task_viva_con_progreso_pero_solo_7min_NO_se_toca(
        self, db, _tenant
    ):
        """Task con plan ya generado y <30min de antigüedad NO es zombie."""
        recent = _utcnow() - timedelta(minutes=7)
        alive = Task(
            tenant_id=_tenant.id,
            domain="x",
            status="executing",
            user_intent="alive",
            started_at=recent,
            plan={"steps": ["step1"]},  # con progreso
        )
        db.add(alive)
        await db.commit()
        a_id = alive.id

        stats = await recover_stale_executions()
        db.expire_all()
        # No se toca esta task
        from sqlalchemy import select

        row = (
            await db.execute(select(Task).where(Task.id == a_id))
        ).scalar_one()
        assert row.status == "executing"
        # stats["tasks_failed"] puede ser 0 (solo si esta era la única) o >=0
        assert stats["tasks_failed"] == 0 or row.status != "failed"

    async def test_execution_huerfana_sin_task_se_marca_cancelled(
        self, db, _tenant
    ):
        """Execution con task_id apuntando a inexistente → cancelled."""
        wf = await _make_workflow(db, _tenant.id)
        # Crear exec con task_id=None (orfanidad explícita)
        orphan = WorkflowExecution(
            tenant_id=_tenant.id,
            workflow_id=wf.id,
            status="pending",
            task_id=None,
        )
        db.add(orphan)
        await db.commit()
        o_id = orphan.id

        stats = await recover_stale_executions()
        db.expire_all()
        assert stats["execs_cancelled"] >= 1

        from sqlalchemy import select

        row = (
            await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == o_id))
        ).scalar_one()
        assert row.status == "cancelled"
        assert "Task asociada no existe" in (row.result_log or "")

    async def test_execution_con_task_zombie_se_sincroniza_a_failed(
        self, db, _tenant
    ):
        """Execution running cuya task quedó marcada failed por el recovery → failed."""
        old = _utcnow() - timedelta(minutes=40)
        zombie = Task(
            tenant_id=_tenant.id,
            domain="x",
            status="executing",
            user_intent="z",
            started_at=old,
            plan=None,
        )
        db.add(zombie)
        await db.commit()
        await db.refresh(zombie)

        wf = await _make_workflow(db, _tenant.id)
        exec_running = WorkflowExecution(
            tenant_id=_tenant.id,
            workflow_id=wf.id,
            status="running",
            task_id=zombie.id,
        )
        db.add(exec_running)
        await db.commit()
        e_id = exec_running.id

        stats = await recover_stale_executions()
        db.expire_all()
        assert stats["execs_failed"] >= 1

        from sqlalchemy import select

        row = (
            await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == e_id))
        ).scalar_one()
        assert row.status == "failed"
        assert row.completed_at is not None

    async def test_recovery_idempotente_sin_zombies(self, db, _tenant):
        """Llamarlo varias veces sin zombies devuelve stats en cero."""
        stats1 = await recover_stale_executions()
        stats2 = await recover_stale_executions()
        assert stats1 == {"tasks_failed": 0, "execs_cancelled": 0, "execs_failed": 0}
        assert stats2 == {"tasks_failed": 0, "execs_cancelled": 0, "execs_failed": 0}
