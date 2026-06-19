"""Tests para app.services.workflow.approval.

Cubre las 3 funciones públicas:
  - list_pending: filtra status=pending y ordena por expires_at
  - decide: happy paths (approved/rejected) + edge cases (no existe, ya cerrada, expirada)
  - cleanup_all: cancela tasks y executions asociados a aprobaciones pendientes
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.db.models.models import PendingApproval, Task, Tenant
from app.services.workflow import approval as svc


@pytest.fixture
async def _ctx(db):
    """Crea tenant + user y devuelve sus ids para los tests."""
    from app.db.models.auth import User

    tenant = Tenant(
        id=uuid4(),
        name="Test Approval",
        nif=f"A{uuid4().int % 10**8:08d}",
    )
    db.add(tenant)
    await db.commit()

    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email=f"u-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
        role="admin",
    )
    db.add(user)
    await db.commit()
    return tenant, user.id


def _utcnow():
    return datetime.now(timezone.utc)


async def _make_task(db, tenant_id, status="awaiting_approval"):
    t = Task(tenant_id=tenant_id, domain="x", user_intent="x", status=status)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


async def _make_approval(
    db, tenant_id, task_id, expires_in_minutes=30, status="pending", execution_id=None,
):
    a = PendingApproval(
        task_id=task_id,
        tenant_id=tenant_id,
        action_description="x",
        action_payload={},
        risk_level="LOW",
        expires_at=_utcnow() + timedelta(minutes=expires_in_minutes),
        status=status,
        execution_id=execution_id,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


# ── list_pending ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestListPending:
    async def test_devuelve_solo_pending(self, db, _ctx):
        tenant, _ = _ctx
        task = await _make_task(db, tenant.id)
        a1 = await _make_approval(db, tenant.id, task.id)  # pending
        a2 = await _make_approval(db, tenant.id, task.id, status="approved")
        a3 = await _make_approval(db, tenant.id, task.id, status="rejected")

        pendings = await svc.list_pending(db, tenant.id)
        ids = {p.id for p in pendings}
        assert a1.id in ids
        assert a2.id not in ids
        assert a3.id not in ids

    async def test_ordenado_por_expires_at_asc(self, db, _ctx):
        tenant, _ = _ctx
        task = await _make_task(db, tenant.id)
        # later expira en 60, sooner en 5
        later = await _make_approval(db, tenant.id, task.id, expires_in_minutes=60)
        sooner = await _make_approval(db, tenant.id, task.id, expires_in_minutes=5)

        pendings = await svc.list_pending(db, tenant.id)
        # Primero el que expira antes
        assert pendings[0].id == sooner.id
        assert pendings[1].id == later.id

    async def test_aislamiento_por_tenant(self, db, _ctx):
        tenant, _ = _ctx
        other_tenant = Tenant(
            id=uuid4(), name="Other", nif=f"O{uuid4().int % 10**8:08d}"
        )
        db.add(other_tenant)
        await db.commit()

        my_task = await _make_task(db, tenant.id)
        my_app = await _make_approval(db, tenant.id, my_task.id)

        their_task = await _make_task(db, other_tenant.id)
        their_app = await _make_approval(db, other_tenant.id, their_task.id)

        pendings = await svc.list_pending(db, tenant.id)
        ids = {p.id for p in pendings}
        assert my_app.id in ids
        assert their_app.id not in ids


# ── decide ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDecide:
    async def test_approved_happy_path(self, db, _ctx):
        tenant, user_id = _ctx
        task = await _make_task(db, tenant.id)
        app = await _make_approval(db, tenant.id, task.id)

        # Mock _resume_after_approval para no dispatchar a worker real
        with patch.object(svc, "_resume_after_approval", new=AsyncMock()):
            result = await svc.decide(
                db, tenant.id, user_id, app.id, approved=True
            )
        assert result.status == "approved"
        assert result.approved_by == user_id
        assert result.approved_at is not None

    async def test_rejected_con_razon(self, db, _ctx):
        tenant, user_id = _ctx
        task = await _make_task(db, tenant.id)
        app = await _make_approval(db, tenant.id, task.id)

        result = await svc.decide(
            db, tenant.id, user_id, app.id,
            approved=False, rejection_reason="datos incompletos",
        )
        assert result.status == "rejected"
        assert result.rejection_reason == "datos incompletos"

    async def test_rechazo_si_no_existe(self, db, _ctx):
        tenant, user_id = _ctx
        with pytest.raises(LookupError, match="no encontrada"):
            await svc.decide(db, tenant.id, user_id, uuid4(), approved=True)

    async def test_rechazo_si_ya_cerrada(self, db, _ctx):
        tenant, user_id = _ctx
        task = await _make_task(db, tenant.id)
        app = await _make_approval(db, tenant.id, task.id, status="approved")
        with pytest.raises(ValueError, match="Ya fue resuelta"):
            await svc.decide(db, tenant.id, user_id, app.id, approved=True)

    async def test_marca_expirada_si_pasó_expires_at(self, db, _ctx):
        tenant, user_id = _ctx
        task = await _make_task(db, tenant.id)
        # Crear con expires_at en el pasado
        a = PendingApproval(
            task_id=task.id,
            tenant_id=tenant.id,
            action_description="x",
            action_payload={},
            risk_level="LOW",
            expires_at=_utcnow() - timedelta(minutes=5),  # ya expirada
            status="pending",
        )
        db.add(a)
        await db.commit()
        await db.refresh(a)

        with pytest.raises(TimeoutError, match="expirad"):
            await svc.decide(db, tenant.id, user_id, a.id, approved=True)

        # El status quedó "expired" tras el commit
        await db.refresh(a)
        assert a.status == "expired"

    async def test_aislamiento_por_tenant(self, db, _ctx):
        """Aprobación de otro tenant no debe encontrarse."""
        tenant, user_id = _ctx
        other = Tenant(
            id=uuid4(), name="Other", nif=f"O{uuid4().int % 10**8:08d}"
        )
        db.add(other)
        await db.commit()
        their_task = await _make_task(db, other.id)
        their_app = await _make_approval(db, other.id, their_task.id)

        with pytest.raises(LookupError):
            await svc.decide(db, tenant.id, user_id, their_app.id, approved=True)


# ── cleanup_all ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCleanupAll:
    async def test_borra_todas_y_devuelve_count(self, db, _ctx):
        tenant, _ = _ctx
        task = await _make_task(db, tenant.id)
        await _make_approval(db, tenant.id, task.id)
        await _make_approval(db, tenant.id, task.id, status="approved")
        await _make_approval(db, tenant.id, task.id, status="rejected")

        deleted = await svc.cleanup_all(db, tenant.id)
        assert deleted == 3

        from sqlalchemy import select
        remaining = (
            await db.execute(select(PendingApproval).where(PendingApproval.tenant_id == tenant.id))
        ).scalars().all()
        assert remaining == []

    async def test_cancela_tasks_de_aprobaciones_pending(self, db, _ctx):
        tenant, _ = _ctx
        task = await _make_task(db, tenant.id, status="awaiting_approval")
        await _make_approval(db, tenant.id, task.id)

        # Mock cancel_task (best-effort, no romper si falla)
        with patch("app.services.workflow.task_dispatch.cancel_task", new=AsyncMock()):
            await svc.cleanup_all(db, tenant.id)

        from sqlalchemy import select
        refreshed = (
            await db.execute(select(Task).where(Task.id == task.id))
        ).scalar_one()
        assert refreshed.status == "cancelled"

    async def test_no_toca_tasks_terminales(self, db, _ctx):
        tenant, _ = _ctx
        done_task = await _make_task(db, tenant.id, status="done")
        await _make_approval(db, tenant.id, done_task.id)

        with patch("app.services.workflow.task_dispatch.cancel_task", new=AsyncMock()):
            await svc.cleanup_all(db, tenant.id)

        from sqlalchemy import select
        refreshed = (
            await db.execute(select(Task).where(Task.id == done_task.id))
        ).scalar_one()
        assert refreshed.status == "done"  # no se tocó

    async def test_aislamiento_por_tenant(self, db, _ctx):
        tenant, _ = _ctx
        other = Tenant(
            id=uuid4(), name="Other", nif=f"O{uuid4().int % 10**8:08d}"
        )
        db.add(other)
        await db.commit()
        my_task = await _make_task(db, tenant.id)
        their_task = await _make_task(db, other.id)
        await _make_approval(db, tenant.id, my_task.id)
        their_app = await _make_approval(db, other.id, their_task.id)

        with patch("app.services.workflow.task_dispatch.cancel_task", new=AsyncMock()):
            deleted = await svc.cleanup_all(db, tenant.id)
        # Solo mi aprobación borrada
        assert deleted == 1
        # La del otro sigue
        from sqlalchemy import select
        survivor = (
            await db.execute(select(PendingApproval).where(PendingApproval.id == their_app.id))
        ).scalar_one_or_none()
        assert survivor is not None

    async def test_devuelve_0_si_no_hay_aprobaciones(self, db, _ctx):
        tenant, _ = _ctx
        deleted = await svc.cleanup_all(db, tenant.id)
        assert deleted == 0
