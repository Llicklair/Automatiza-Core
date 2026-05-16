"""Tests del agregador de coste por task (UI.COST)."""
from decimal import Decimal
from uuid import uuid4

import pytest
from app.db.models.tasks import AgentExecutionTrace, Task
from app.services.ai.task_cost import summarize_task_cost


def _trace(*, tenant_id, task_id, agent: str, tin: int, tout: int, eur: str) -> AgentExecutionTrace:
    return AgentExecutionTrace(
        tenant_id=tenant_id,
        task_id=task_id,
        agent_name=agent,
        tokens_in=tin,
        tokens_out=tout,
        cost_eur=Decimal(eur),
    )


def _task(tenant_id, user_id) -> Task:
    return Task(
        tenant_id=tenant_id,
        created_by=user_id,
        domain="chat",
        user_intent="test cost",
        status="executing",
    )


@pytest.mark.asyncio
class TestTaskCost:
    async def test_task_inexistente_devuelve_status_none(
        self, db, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user

        result = await summarize_task_cost(
            db, tenant_id=tenant.id, task_id=uuid4(),
        )
        assert result["task_status"] is None
        assert result["tokens_total"] == 0
        assert result["cost_eur"] == 0.0
        assert result["agents"] == []

    async def test_task_sin_trazas_devuelve_ceros(
        self, db, seed_tenant_and_user
    ):
        tenant, user, _t = seed_tenant_and_user
        task = _task(tenant.id, user.id)
        db.add(task)
        await db.flush()

        result = await summarize_task_cost(
            db, tenant_id=tenant.id, task_id=task.id,
        )
        assert result["task_status"] == "executing"
        assert result["tokens_total"] == 0
        assert result["cost_eur"] == 0.0
        assert result["trace_count"] == 0

    async def test_agrega_tokens_y_eur(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        task = _task(tenant.id, user.id)
        db.add(task)
        await db.flush()

        db.add_all([
            _trace(tenant_id=tenant.id, task_id=task.id, agent="billing", tin=100, tout=50, eur="0.0030"),
            _trace(tenant_id=tenant.id, task_id=task.id, agent="billing", tin=200, tout=80, eur="0.0050"),
            _trace(tenant_id=tenant.id, task_id=task.id, agent="accounting", tin=50, tout=20, eur="0.0010"),
        ])
        await db.flush()

        result = await summarize_task_cost(
            db, tenant_id=tenant.id, task_id=task.id,
        )

        assert result["tokens_in"] == 350
        assert result["tokens_out"] == 150
        assert result["tokens_total"] == 500
        assert result["cost_eur"] == pytest.approx(0.009)
        assert result["trace_count"] == 3

        # Desglose por agente
        agents = {a["agent"]: a for a in result["agents"]}
        assert "billing" in agents
        assert agents["billing"]["tokens"] == 100 + 50 + 200 + 80
        assert agents["accounting"]["tokens"] == 70

    async def test_aislamiento_entre_tenants(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        task = _task(tenant.id, user.id)
        db.add(task)
        await db.flush()

        db.add(_trace(
            tenant_id=tenant.id, task_id=task.id,
            agent="billing", tin=100, tout=50, eur="0.0030",
        ))
        await db.flush()

        # Otro tenant intenta consultar — task no existe para él
        result = await summarize_task_cost(
            db, tenant_id=uuid4(), task_id=task.id,
        )
        assert result["task_status"] is None
        assert result["tokens_total"] == 0
