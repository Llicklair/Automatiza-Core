"""Cross-tenant isolation tests for TokenLedger queries.

Proves that get_employee_spend and get_employee_ledger filter by tenant_id —
even if an attacker knows another tenant's employee UUID, no data leaks.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ai_employees import AIEmployee, TokenLedger
from app.db.models.auth import Tenant
from app.services.ai.employee_crud import get_employee_ledger, get_employee_spend


@pytest_asyncio.fixture
async def two_tenants_with_ledger(db: AsyncSession):
    """Create two tenants, each with one AI employee and one TokenLedger row."""
    tenant_a = Tenant(id=uuid.uuid4(), name="Tenant A", nif="A11111111", plan="starter")
    tenant_b = Tenant(id=uuid.uuid4(), name="Tenant B", nif="B22222222", plan="starter")
    db.add_all([tenant_a, tenant_b])
    await db.flush()

    emp_a = AIEmployee(
        id=uuid.uuid4(), tenant_id=tenant_a.id, name="Ana A", role="Billing A",
        domain="billing", system_prompt="A", budget_limit_usd=10, status="idle",
    )
    emp_b = AIEmployee(
        id=uuid.uuid4(), tenant_id=tenant_b.id, name="Ana B", role="Billing B",
        domain="billing", system_prompt="B", budget_limit_usd=10, status="idle",
    )
    db.add_all([emp_a, emp_b])
    await db.flush()

    db.add_all([
        TokenLedger(
            id=uuid.uuid4(), tenant_id=tenant_a.id, employee_id=emp_a.id,
            task_id=uuid.uuid4(), prompt_tokens=1000, completion_tokens=500,
            cost_usd=Decimal("3.50"), llm_provider="anthropic",
        ),
        TokenLedger(
            id=uuid.uuid4(), tenant_id=tenant_b.id, employee_id=emp_b.id,
            task_id=uuid.uuid4(), prompt_tokens=2000, completion_tokens=800,
            cost_usd=Decimal("7.25"), llm_provider="anthropic",
        ),
    ])
    await db.commit()

    return tenant_a, tenant_b, emp_a, emp_b


@pytest.mark.asyncio
async def test_spend_returns_data_for_correct_tenant(db, two_tenants_with_ledger):
    tenant_a, _, emp_a, _ = two_tenants_with_ledger
    spent = await get_employee_spend(str(emp_a.id), str(tenant_a.id), db)
    assert spent == pytest.approx(3.50)


@pytest.mark.asyncio
async def test_spend_returns_zero_when_employee_id_belongs_to_other_tenant(
    db, two_tenants_with_ledger
):
    """Critical: querying empA's spend with tenantB credentials must return 0."""
    _, tenant_b, emp_a, _ = two_tenants_with_ledger
    spent = await get_employee_spend(str(emp_a.id), str(tenant_b.id), db)
    assert spent == 0.0, "Cross-tenant data leak: tenant B saw tenant A's spend"


@pytest.mark.asyncio
async def test_ledger_returns_only_own_tenant_entries(db, two_tenants_with_ledger):
    tenant_a, _, emp_a, _ = two_tenants_with_ledger
    result = await get_employee_ledger(str(emp_a.id), str(tenant_a.id), db)
    assert result["total_calls"] == 1
    assert result["total_cost_usd"] == pytest.approx(3.50)
    assert len(result["entries"]) == 1


@pytest.mark.asyncio
async def test_ledger_returns_empty_for_other_tenant(db, two_tenants_with_ledger):
    """Critical: tenant B querying empA's ledger must see nothing."""
    _, tenant_b, emp_a, _ = two_tenants_with_ledger
    result = await get_employee_ledger(str(emp_a.id), str(tenant_b.id), db)
    assert result["total_calls"] == 0
    assert result["total_cost_usd"] == 0.0
    assert result["entries"] == []


@pytest.mark.asyncio
async def test_ledger_aggregates_only_correct_tenant(db, two_tenants_with_ledger):
    """If both tenants have the SAME employee UUID by collision, aggregates stay separate."""
    tenant_a, tenant_b, _, _ = two_tenants_with_ledger
    # Inject a forged ledger row in tenant_b with the SAME employee_id as some random one
    forged_id = uuid.uuid4()
    db.add(TokenLedger(
        id=uuid.uuid4(), tenant_id=tenant_a.id, employee_id=forged_id,
        task_id=uuid.uuid4(), prompt_tokens=10, completion_tokens=5,
        cost_usd=Decimal("0.10"), llm_provider="mock",
    ))
    db.add(TokenLedger(
        id=uuid.uuid4(), tenant_id=tenant_b.id, employee_id=forged_id,
        task_id=uuid.uuid4(), prompt_tokens=99, completion_tokens=99,
        cost_usd=Decimal("99.99"), llm_provider="mock",
    ))
    await db.commit()

    spent_a = await get_employee_spend(str(forged_id), str(tenant_a.id), db)
    spent_b = await get_employee_spend(str(forged_id), str(tenant_b.id), db)
    assert spent_a == pytest.approx(0.10)
    assert spent_b == pytest.approx(99.99)
    assert spent_a != spent_b
