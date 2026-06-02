"""Camino del dinero: persistencia del consumo LLM + tope agregado por tenant.

- Persistencia por snapshot: record() en memoria → persist_to_db() → load_from_db()
  restaura el dashboard (sobrevive a reinicios).
- check_tenant_budget: desactivado por defecto; bloquea/permite según el tope.
"""

from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.llm_usage import LlmUsageMonthly
from app.db.models.models import TokenLedger, Tenant
from app.services import llm_usage_tracker
from app.services.agent_budget import check_tenant_budget


async def _seed_tenant() -> str:
    async with AsyncSessionLocal() as db:
        tenant = Tenant(id=uuid4(), name="Money Path S.L.", nif="B55667788", plan="starter")
        db.add(tenant)
        await db.commit()
        return str(tenant.id)


# ── Persistencia del consumo LLM ──────────────────────────────────────────────


async def test_usage_persist_and_reload_roundtrip():
    tenant_id = await _seed_tenant()
    llm_usage_tracker.flush_tenant(tenant_id)
    llm_usage_tracker.record(tenant_id, "billing", "anthropic", 1000, 500)
    llm_usage_tracker.record(tenant_id, "billing", "anthropic", 200, 100)
    llm_usage_tracker.record(tenant_id, "hr", "openai", 50, 20)

    written = await llm_usage_tracker.persist_to_db()
    assert written >= 2

    # Simula reinicio: vacía la memoria y recarga desde la DB.
    llm_usage_tracker.flush_tenant(tenant_id)
    assert llm_usage_tracker.get_monthly_stats(tenant_id) == []
    loaded = await llm_usage_tracker.load_from_db()
    assert loaded >= 2

    stats = llm_usage_tracker.get_monthly_stats(tenant_id)
    assert stats, "el dashboard debería restaurarse tras recargar"
    month = stats[0]
    assert month["total_calls"] == 3
    assert month["total_tokens_in"] == 1250  # 1000 + 200 + 50
    assert month["total_tokens_out"] == 620  # 500 + 100 + 20
    llm_usage_tracker.flush_tenant(tenant_id)


async def test_usage_persist_is_idempotent():
    tenant_id = await _seed_tenant()
    llm_usage_tracker.flush_tenant(tenant_id)
    llm_usage_tracker.record(tenant_id, "billing", "anthropic", 1000, 500)

    await llm_usage_tracker.persist_to_db()
    await llm_usage_tracker.persist_to_db()  # segundo flush no debe duplicar

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(LlmUsageMonthly).where(LlmUsageMonthly.tenant_id == UUID(tenant_id))
            )
        ).scalars().all()
    assert len(rows) == 1
    assert rows[0].tokens_in == 1000
    assert rows[0].tokens_out == 500
    llm_usage_tracker.flush_tenant(tenant_id)


# ── Tope agregado por tenant ──────────────────────────────────────────────────


async def _seed_token_ledger(tenant_id: str, cost: float) -> None:
    async with AsyncSessionLocal() as db:
        db.add(
            TokenLedger(
                tenant_id=UUID(tenant_id),
                employee_id=None,
                prompt_tokens=1000,
                completion_tokens=500,
                cost_usd=cost,
                llm_provider="anthropic",
            )
        )
        await db.commit()


async def test_tenant_budget_disabled_by_default():
    tenant_id = await _seed_tenant()
    await _seed_token_ledger(tenant_id, 999.0)  # gasto alto, pero tope desactivado
    async with AsyncSessionLocal() as db:
        assert await check_tenant_budget(tenant_id, db) is True


async def test_tenant_budget_blocks_when_over(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "TENANT_MONTHLY_LLM_BUDGET_USD", 1.0)
    tenant_id = await _seed_tenant()
    await _seed_token_ledger(tenant_id, 5.0)  # 5$ > 1$
    async with AsyncSessionLocal() as db:
        assert await check_tenant_budget(tenant_id, db) is False


async def test_tenant_budget_allows_when_under(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "TENANT_MONTHLY_LLM_BUDGET_USD", 100.0)
    tenant_id = await _seed_tenant()
    await _seed_token_ledger(tenant_id, 5.0)  # 5$ < 100$
    async with AsyncSessionLocal() as db:
        assert await check_tenant_budget(tenant_id, db) is True
