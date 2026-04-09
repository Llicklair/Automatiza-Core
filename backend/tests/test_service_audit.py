"""Tests para app.services.audit — logging inmutable de acciones."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.audit import log_action, log_llm_call
from app.db.models.models import AuditLog


class TestAuditService:
    @pytest.mark.asyncio
    async def test_log_action_creates_record(self, db: AsyncSession, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        await log_action(
            db=db,
            tenant_id=tenant.id,
            agent_name="billing_agent",
            action_type="create_invoice",
            status="success",
            input_data={"client": "ACME"},
            output_data={"invoice_id": "F-2026-001"},
        )
        await db.flush()

        result = await db.execute(select(AuditLog))
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].agent_name == "billing_agent"
        assert logs[0].action_type == "create_invoice"
        assert logs[0].status == "success"

    @pytest.mark.asyncio
    async def test_log_action_with_error(self, db: AsyncSession, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        await log_action(
            db=db,
            tenant_id=tenant.id,
            agent_name="hr_agent",
            action_type="create_employee",
            status="error",
            error_detail="NIF duplicado",
        )
        await db.flush()

        result = await db.execute(select(AuditLog))
        log = result.scalars().first()
        assert log.status == "error"
        assert log.error_detail == "NIF duplicado"

    @pytest.mark.asyncio
    async def test_log_llm_call(self, db: AsyncSession, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        await log_llm_call(
            db=db,
            tenant_id=tenant.id,
            agent_name="orchestrator",
            action_type="classify_intent",
            prompt="Clasifica esta intencion",
            response="billing.create_invoice",
        )
        await db.flush()

        result = await db.execute(select(AuditLog))
        log = result.scalars().first()
        assert log.agent_name == "orchestrator"
        assert log.llm_prompt == "Clasifica esta intencion"

    @pytest.mark.asyncio
    async def test_log_action_with_task_id(self, db: AsyncSession, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from uuid import uuid4
        task_id = uuid4()
        await log_action(
            db=db,
            tenant_id=tenant.id,
            agent_name="documents_agent",
            action_type="upload_document",
            status="success",
            task_id=task_id,
        )
        await db.flush()

        result = await db.execute(select(AuditLog))
        log = result.scalars().first()
        assert log.task_id == task_id
