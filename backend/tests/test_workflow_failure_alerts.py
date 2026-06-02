"""Alertado de fallos de automatizaciones desatendidas (#5).

El sweep `check_failed_workflow_executions` notifica al gestor las ejecuciones
de workflow que fallaron y aún no se notificaron. Las manuales no avisan (el
usuario ya lo ve en la UI). El flag `notified` evita duplicar.
"""

from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import Tenant, Workflow, WorkflowExecution
from app.db.models.notifications import Notification
from app.workers.tasks_scheduler import _check_failed_workflow_executions


async def _seed_failed_execution(trigger_payload: dict | None) -> tuple[str, str]:
    async with AsyncSessionLocal() as db:
        tenant = Tenant(
            id=uuid4(),
            name="Alert S.L.",
            nif=f"B{str(uuid4().int)[:8]}",
            plan="starter",
        )
        db.add(tenant)
        await db.flush()
        wf = Workflow(
            id=uuid4(),
            tenant_id=tenant.id,
            name="Resumen IVA mensual",
            trigger_type="schedule_based",
            action_type="agent_task",
        )
        db.add(wf)
        await db.flush()
        ex = WorkflowExecution(
            id=uuid4(),
            workflow_id=wf.id,
            tenant_id=tenant.id,
            status="failed",
            trigger_payload=trigger_payload,
            result_log="Error lanzando orchestrator: boom",
        )
        db.add(ex)
        await db.commit()
        return str(tenant.id), str(ex.id)


async def _notifications(tenant_id: str) -> list[Notification]:
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Notification).where(Notification.tenant_id == UUID(tenant_id))
        )
        return list(res.scalars().all())


async def _is_notified(ex_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(WorkflowExecution.notified).where(WorkflowExecution.id == UUID(ex_id))
        )
        return bool(res.scalar_one())


async def test_scheduled_failure_notifies_gestor():
    tenant_id, ex_id = await _seed_failed_execution({"source": "apscheduler"})
    await _check_failed_workflow_executions()

    notifs = await _notifications(tenant_id)
    assert len(notifs) == 1
    assert notifs[0].kind == "error"
    assert "falló" in notifs[0].title
    assert notifs[0].payload["execution_id"] == ex_id
    assert await _is_notified(ex_id) is True


async def test_manual_failure_not_notified():
    # Manual = trigger_payload sin 'source' (el usuario ya lo ve en la UI).
    tenant_id, ex_id = await _seed_failed_execution(None)
    await _check_failed_workflow_executions()

    assert await _notifications(tenant_id) == []
    # Aun así se marca notified para no re-escanearla cada 10 min.
    assert await _is_notified(ex_id) is True


async def test_sweep_is_idempotent():
    tenant_id, _ex_id = await _seed_failed_execution({"source": "catchup"})
    await _check_failed_workflow_executions()
    await _check_failed_workflow_executions()  # segunda pasada no debe duplicar

    assert len(await _notifications(tenant_id)) == 1
