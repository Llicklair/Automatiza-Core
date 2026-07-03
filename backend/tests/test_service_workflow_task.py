"""Tests para app.services.workflow.task.

Cubre el bug del cleanup vs WORM (soft-delete via is_deleted) — lessons
2026-05-19. cleanup_tasks ya no DELETE FROM tasks; marca is_deleted=True.
audit_log queda intacto (WORM compliance) y FK no se rompe.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from app.db.models.models import AuditLog, PendingApproval, Task, Tenant
from app.services.workflow import task as task_service


@pytest.fixture
async def _tenant(db):
    t = Tenant(
        id=uuid4(),
        name="Test Cleanup",
        nif=f"A{uuid4().int % 10**8:08d}",
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


@pytest.mark.asyncio
class TestCleanupTasks:
    async def test_cleanup_marca_is_deleted_y_preserva_audit(self, db, _tenant):
        """Soft-delete: tasks invisibles pero audit_log intacto."""
        # arrange: 2 tareas terminales + 1 audit_log apuntando a una
        t1 = Task(
            tenant_id=_tenant.id, domain="billing", status="done", user_intent="x"
        )
        t2 = Task(
            tenant_id=_tenant.id, domain="hr", status="failed", user_intent="y"
        )
        db.add_all([t1, t2])
        await db.commit()

        log = AuditLog(
            task_id=t1.id,
            tenant_id=_tenant.id,
            agent_name="billing",
            action_type="create_invoice",
            status="ok",
            executed_at=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.commit()

        # act
        result = await task_service.cleanup_tasks(db, tenant_id=_tenant.id)

        # assert: ambas tareas reportadas, ninguna cancelada (estaban terminales)
        assert result == {"deleted": 2, "cancelled": 0}

        # list_tasks no las debe ver
        visibles = await task_service.list_tasks(db, tenant_id=_tenant.id)
        assert visibles == []

        # get_task tampoco
        with pytest.raises(LookupError):
            await task_service.get_task(db, task_id=t1.id, tenant_id=_tenant.id)

        # audit_log intacto (WORM compliance)
        from sqlalchemy import select

        rows = (await db.execute(select(AuditLog).where(AuditLog.id == log.id))).scalars().all()
        assert len(rows) == 1
        assert rows[0].task_id == t1.id  # FK no rota: task existe (is_deleted=True)

        # task real sigue en DB
        raw = (
            await db.execute(select(Task).where(Task.id == t1.id))
        ).scalar_one()
        assert raw.is_deleted is True

    async def test_cleanup_cancela_activas_y_las_oculta(self, db, _tenant):
        """Tareas en estado activo se cancelan y luego se soft-deletean."""
        t_active = Task(
            tenant_id=_tenant.id,
            domain="billing",
            status="executing",
            user_intent="x",
        )
        db.add(t_active)
        await db.commit()

        result = await task_service.cleanup_tasks(db, tenant_id=_tenant.id)
        assert result == {"deleted": 1, "cancelled": 1}

        from sqlalchemy import select

        raw = (
            await db.execute(select(Task).where(Task.id == t_active.id))
        ).scalar_one()
        assert raw.status == "cancelled"
        assert raw.is_deleted is True

    async def test_cleanup_borra_pending_approvals(self, db, _tenant):
        """pending_approvals (no WORM) se borran físicamente."""
        t = Task(tenant_id=_tenant.id, domain="hr", status="done", user_intent="x")
        db.add(t)
        await db.commit()

        pa = PendingApproval(
            task_id=t.id,
            tenant_id=_tenant.id,
            action_description="x",
            action_payload={},
            risk_level="LOW",
            expires_at=datetime.now(timezone.utc),
            status="pending",
        )
        db.add(pa)
        await db.commit()

        await task_service.cleanup_tasks(db, tenant_id=_tenant.id)

        from sqlalchemy import select

        remaining = (
            await db.execute(select(PendingApproval).where(PendingApproval.task_id == t.id))
        ).scalars().all()
        assert remaining == []

    async def test_cleanup_idempotente_si_no_hay_tareas(self, db, _tenant):
        result = await task_service.cleanup_tasks(db, tenant_id=_tenant.id)
        assert result == {"deleted": 0, "cancelled": 0}

    async def test_cleanup_no_toca_tasks_de_otros_tenants(self, db, _tenant):
        other = Tenant(
            id=uuid4(),
            name="Other",
            nif=f"B{uuid4().int % 10**8:08d}",
        )
        db.add(other)
        await db.commit()

        mine = Task(
            tenant_id=_tenant.id, domain="x", status="done", user_intent="m"
        )
        theirs = Task(
            tenant_id=other.id, domain="x", status="done", user_intent="t"
        )
        db.add_all([mine, theirs])
        await db.commit()

        await task_service.cleanup_tasks(db, tenant_id=_tenant.id)

        from sqlalchemy import select

        raw_theirs = (
            await db.execute(select(Task).where(Task.id == theirs.id))
        ).scalar_one()
        assert raw_theirs.is_deleted is False


@pytest.mark.asyncio
class TestListAndGet:
    async def test_list_excluye_soft_deleted(self, db, _tenant):
        keep = Task(
            tenant_id=_tenant.id, domain="x", status="done", user_intent="k"
        )
        gone = Task(
            tenant_id=_tenant.id,
            domain="x",
            status="done",
            user_intent="g",
            is_deleted=True,
        )
        db.add_all([keep, gone])
        await db.commit()

        visibles = await task_service.list_tasks(db, tenant_id=_tenant.id)
        ids = {t.id for t in visibles}
        assert keep.id in ids
        assert gone.id not in ids

    async def test_get_404_si_soft_deleted(self, db, _tenant):
        gone = Task(
            tenant_id=_tenant.id,
            domain="x",
            status="done",
            user_intent="g",
            is_deleted=True,
        )
        db.add(gone)
        await db.commit()

        with pytest.raises(LookupError):
            await task_service.get_task(db, task_id=gone.id, tenant_id=_tenant.id)


@pytest.mark.asyncio
async def test_exec_create_invoice_produces_proforma(db, _tenant):
    """Opción A (candado): la acción de aprobación 'create_invoice' NO emite
    factura fiscal — crea una PROFORMA sin número ad-hoc 'FAC-...'
    (invoice_number=NULL, invoice_type='proforma'). Regresión de
    services/workflow/approval_actions._exec_create_invoice."""
    from sqlalchemy import select

    from app.db.models.models import Invoice
    from app.services.workflow.approval_actions import _exec_create_invoice

    ok, msg = await _exec_create_invoice(
        {
            "amount_base": "100",
            "vat_rate": "21",
            "concept": "Servicio por aprobación",
            "client_name": "Cliente Aprobación",
        },
        db,
        str(_tenant.id),
    )
    assert ok is True
    assert "Proforma" in msg

    res = await db.execute(select(Invoice).where(Invoice.tenant_id == _tenant.id))
    inv = res.scalars().one()
    assert inv.invoice_number is None
    assert inv.invoice_type == "proforma"
