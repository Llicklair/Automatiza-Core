"""Tests para AgentExecutionTrace (SEC.WORM + AI Act compliance)."""
import hashlib
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models.tasks import AgentExecutionTrace
from app.services.observability.agent_trace import record_agent_execution


@pytest.mark.asyncio
class TestAgentExecutionTrace:
    async def test_traza_minima_se_persiste(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        trace = await record_agent_execution(
            db,
            tenant_id=tenant.id,
            agent_name="billing",
        )
        await db.commit()

        assert trace.id is not None
        assert trace.agent_name == "billing"
        assert trace.status == "ok"
        assert trace.tenant_id == tenant.id

    async def test_prompt_y_output_se_hashean(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        prompt = "Eres un asistente fiscal. Genera el modelo 303 para Q1 2026."
        output = "He generado el modelo 303 con base 10000 e IVA 2100..."

        trace = await record_agent_execution(
            db,
            tenant_id=tenant.id,
            agent_name="billing",
            prompt_text=prompt,
            output_text=output,
        )
        await db.commit()

        expected_prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        expected_output_hash = hashlib.sha256(output.encode("utf-8")).hexdigest()
        assert trace.prompt_hash == expected_prompt_hash
        assert trace.output_hash == expected_output_hash
        assert len(trace.prompt_hash) == 64
        assert len(trace.output_hash) == 64

    async def test_tokens_y_coste_se_persisten(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        trace = await record_agent_execution(
            db,
            tenant_id=tenant.id,
            agent_name="billing",
            llm_provider="anthropic",
            llm_model="claude-3-7-sonnet",
            tokens_in=1200,
            tokens_out=420,
            cost_eur=Decimal("0.0181"),
            duration_ms=2350,
        )
        await db.commit()

        assert trace.tokens_in == 1200
        assert trace.tokens_out == 420
        assert trace.cost_eur == Decimal("0.0181")
        assert trace.duration_ms == 2350
        assert trace.llm_provider == "anthropic"
        assert trace.llm_model == "claude-3-7-sonnet"

    async def test_tool_calls_json_se_persiste(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        tool_calls = [
            {"name": "create_invoice", "args": {"client": "Acme"}},
            {"name": "send_email", "args": {"to": "a@b.com"}},
        ]
        trace = await record_agent_execution(
            db,
            tenant_id=tenant.id,
            agent_name="billing",
            tool_calls=tool_calls,
        )
        await db.commit()

        await db.refresh(trace)
        assert trace.tool_calls_json == tool_calls

    async def test_status_error_con_error_class(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        trace = await record_agent_execution(
            db,
            tenant_id=tenant.id,
            agent_name="banking",
            status="error",
            error_class="anthropic.RateLimitError",
        )
        await db.commit()

        assert trace.status == "error"
        assert trace.error_class == "anthropic.RateLimitError"

    async def test_execution_id_link(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        exec_id = uuid4()
        await record_agent_execution(
            db,
            tenant_id=tenant.id,
            agent_name="billing",
            execution_id=exec_id,
        )
        await db.commit()

        result = await db.execute(
            select(AgentExecutionTrace).where(AgentExecutionTrace.execution_id == exec_id)
        )
        traces = list(result.scalars().all())
        assert len(traces) == 1

    async def test_prompt_none_devuelve_hash_none(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        trace = await record_agent_execution(
            db,
            tenant_id=tenant.id,
            agent_name="orchestrator",
            prompt_text=None,
            output_text=None,
        )
        await db.commit()
        assert trace.prompt_hash is None
        assert trace.output_hash is None

    async def test_multiples_trazas_misma_execution(self, db, seed_tenant_and_user):
        # Una ejecución de workflow puede tener N invocaciones de agentes.
        tenant, _, _ = seed_tenant_and_user
        exec_id = uuid4()
        for agent in ("orchestrator", "billing", "documents"):
            await record_agent_execution(
                db, tenant_id=tenant.id, agent_name=agent, execution_id=exec_id,
            )
        await db.commit()

        result = await db.execute(
            select(AgentExecutionTrace).where(AgentExecutionTrace.execution_id == exec_id)
        )
        traces = list(result.scalars().all())
        assert len(traces) == 3
        agent_names = {t.agent_name for t in traces}
        assert agent_names == {"orchestrator", "billing", "documents"}
