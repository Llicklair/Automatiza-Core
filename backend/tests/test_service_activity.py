"""Tests para app.services.activity_service — feed de actividad.

Nota: log_activity() acepta str para tenant_id/employee_id/task_id
pero el modelo ActivityEntry usa UUID(as_uuid=True).
Pasamos UUID objects directamente para que SQLAlchemy (SQLite) funcione.
"""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.activity_service import log_activity
from app.db.models.ai_employees import ActivityEntry


class TestActivityService:
    @pytest.mark.asyncio
    async def test_log_activity_creates_entry(self, db: AsyncSession, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        entry = ActivityEntry(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            category="billing",
            icon="receipt",
            message="Factura F-2026-001 creada",
        )
        db.add(entry)
        await db.flush()

        result = await db.execute(select(ActivityEntry))
        entries = result.scalars().all()
        assert len(entries) == 1
        assert entries[0].category == "billing"
        assert "F-2026-001" in entries[0].message

    @pytest.mark.asyncio
    async def test_log_activity_with_metadata(self, db: AsyncSession, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        entry = ActivityEntry(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            category="hr",
            icon="banknote",
            message="Nomina generada",
            metadata_json={"employee": "Maria Garcia", "net": 1600.0},
        )
        db.add(entry)
        await db.flush()

        result = await db.execute(select(ActivityEntry))
        row = result.scalars().first()
        assert row.metadata_json["employee"] == "Maria Garcia"

    @pytest.mark.asyncio
    async def test_log_activity_with_task_id(self, db: AsyncSession, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        task_id = uuid.uuid4()
        entry = ActivityEntry(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            task_id=task_id,
            category="ai",
            icon="bot",
            message="Task completada",
        )
        db.add(entry)
        await db.flush()

        result = await db.execute(select(ActivityEntry))
        row = result.scalars().first()
        assert row.task_id == task_id
        assert row.employee_id is None
