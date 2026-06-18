"""Tests para app.services.workflow.scheduler.

Cubre los 7 helpers DB que la capa scheduler usa para encapsular
los SQLAlchemy calls fuera del worker APScheduler (tasks_scheduler.py).
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from app.db.models.models import Tenant, Workflow, WorkflowExecution
from app.services.workflow.scheduler import (
    create_execution,
    create_task_for_execution,
    get_active_scheduled_workflows,
    get_last_execution,
    get_stuck_executions,
    has_active_execution,
    mark_executions_failed,
)


def _utcnow():
    return datetime.now(timezone.utc)


@pytest.fixture
async def _tenant(db):
    t = Tenant(id=uuid4(), name="Test Sched", nif=f"S{uuid4().int % 10**8:08d}")
    db.add(t)
    await db.commit()
    return t


async def _make_workflow(db, tenant_id, **overrides):
    defaults = dict(
        tenant_id=tenant_id,
        name="WF",
        trigger_type="schedule_based",
        action_type="prompt",
        is_active=True,
    )
    defaults.update(overrides)
    wf = Workflow(**defaults)
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return wf


@pytest.mark.asyncio
class TestGetActiveScheduledWorkflows:
    async def test_devuelve_solo_active_schedule_based(self, db, _tenant):
        active_sched = await _make_workflow(db, _tenant.id)
        inactive = await _make_workflow(db, _tenant.id, is_active=False)
        event_based = await _make_workflow(db, _tenant.id, trigger_type="event_based")
        manual = await _make_workflow(db, _tenant.id, trigger_type="manual")

        result = await get_active_scheduled_workflows(db)
        ids = {w.id for w in result}
        assert active_sched.id in ids
        assert inactive.id not in ids
        assert event_based.id not in ids
        assert manual.id not in ids


@pytest.mark.asyncio
class TestHasActiveExecution:
    async def test_true_si_hay_running(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id)
        db.add(WorkflowExecution(workflow_id=wf.id, tenant_id=_tenant.id, status="running"))
        await db.commit()
        assert await has_active_execution(db, wf.id) is True

    async def test_true_si_hay_pending(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id)
        db.add(WorkflowExecution(workflow_id=wf.id, tenant_id=_tenant.id, status="pending"))
        await db.commit()
        assert await has_active_execution(db, wf.id) is True

    async def test_false_si_solo_terminales(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id)
        for status in ("success", "failed", "cancelled"):
            db.add(WorkflowExecution(workflow_id=wf.id, tenant_id=_tenant.id, status=status))
        await db.commit()
        assert await has_active_execution(db, wf.id) is False

    async def test_false_si_no_hay_ejecuciones(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id)
        assert await has_active_execution(db, wf.id) is False


@pytest.mark.asyncio
class TestGetLastExecution:
    async def test_devuelve_la_mas_reciente(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id)
        old = WorkflowExecution(
            workflow_id=wf.id, tenant_id=_tenant.id, status="success",
            started_at=_utcnow() - timedelta(hours=2),
        )
        new = WorkflowExecution(
            workflow_id=wf.id, tenant_id=_tenant.id, status="failed",
            started_at=_utcnow(),
        )
        db.add_all([old, new])
        await db.commit()

        last = await get_last_execution(db, wf.id)
        assert last is not None
        assert last.id == new.id

    async def test_devuelve_None_si_no_hay(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id)
        assert await get_last_execution(db, wf.id) is None


@pytest.mark.asyncio
class TestCreateExecution:
    async def test_inserta_y_flush(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id)
        payload = {"trigger": "cron"}
        ex = await create_execution(db, wf, payload)
        assert ex.id is not None  # asignado por flush
        assert ex.workflow_id == wf.id
        assert ex.tenant_id == _tenant.id
        assert ex.status == "running"
        assert ex.trigger_payload == payload
        # No commited todavía — caller responsable
        await db.commit()

    async def test_tenant_id_se_propaga_del_workflow(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id)
        ex = await create_execution(db, wf, {})
        assert ex.tenant_id == wf.tenant_id


@pytest.mark.asyncio
class TestCreateTaskForExecution:
    async def test_crea_task_y_vincula_a_execution(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id)
        ex = await create_execution(db, wf, {})
        await db.commit()

        task = await create_task_for_execution(
            db, wf, ex,
            domain="billing",
            user_intent="lanza factura",
            initial_status="pending",
            meta={"x": 1},
        )
        await db.commit()
        await db.refresh(ex)

        assert task.tenant_id == _tenant.id
        assert task.created_by is None  # scheduler no tiene user
        assert task.domain == "billing"
        assert task.user_intent == "lanza factura"
        assert task.status == "pending"
        assert task.additional_metadata == {"x": 1}
        assert ex.task_id == task.id


@pytest.mark.asyncio
class TestGetStuckExecutions:
    async def test_filtra_solo_running_antes_de_cutoff(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id)
        old_running = WorkflowExecution(
            workflow_id=wf.id, tenant_id=_tenant.id, status="running",
            started_at=_utcnow() - timedelta(hours=5),
        )
        recent_running = WorkflowExecution(
            workflow_id=wf.id, tenant_id=_tenant.id, status="running",
            started_at=_utcnow(),
        )
        old_success = WorkflowExecution(
            workflow_id=wf.id, tenant_id=_tenant.id, status="success",
            started_at=_utcnow() - timedelta(hours=5),
        )
        db.add_all([old_running, recent_running, old_success])
        await db.commit()

        cutoff = _utcnow() - timedelta(hours=1)
        stuck = await get_stuck_executions(db, cutoff)
        ids = {e.id for e in stuck}
        assert old_running.id in ids
        assert recent_running.id not in ids  # más reciente que cutoff
        assert old_success.id not in ids  # status != running


@pytest.mark.asyncio
class TestMarkExecutionsFailed:
    async def test_marca_failed_y_appendea_note(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id)
        ex1 = WorkflowExecution(workflow_id=wf.id, tenant_id=_tenant.id, status="running")
        ex2 = WorkflowExecution(
            workflow_id=wf.id, tenant_id=_tenant.id, status="running",
            result_log="parcial:",
        )
        db.add_all([ex1, ex2])
        await db.commit()

        await mark_executions_failed(db, [ex1, ex2], note="timeout 5h")
        await db.commit()

        assert ex1.status == "failed"
        assert ex1.completed_at is not None
        assert "timeout 5h" in ex1.result_log
        # ex2 conserva su log previo
        assert ex2.status == "failed"
        assert "parcial:" in ex2.result_log
        assert "timeout 5h" in ex2.result_log

    async def test_lista_vacia_no_crashea(self, db, _tenant):
        # No debe lanzar
        await mark_executions_failed(db, [], note="x")
