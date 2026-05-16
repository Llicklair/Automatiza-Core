"""Tests for tasks_orchestrator and its helpers in _orchestrator_state.py.

Covers: pure logic (_is_transient_error), DB helpers (_set_agent_status,
_save_final_state, _mark_task_failed, _log_task_completion), and an
end-to-end happy-path with _stream_and_log mocked.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from app.db.models.ai_employees import AIEmployee, TokenLedger
from app.db.models.auth import Tenant
from app.db.models.models import Task, User
from app.workers import _orchestrator_state as _state
from app.workers import tasks_orchestrator as _to
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ── _is_transient_error (pure) ───────────────────────────────────────────────

@pytest.mark.parametrize("exc", [
    ConnectionError("network down"),
    OSError("conn refused"),
    TimeoutError("slow"),
    Exception("HTTP 429 rate limit"),
    Exception("service unavailable"),
    Exception("anthropic overloaded"),
    Exception("connection reset by peer"),
])
def test_is_transient_returns_true(exc):
    assert _to._is_transient_error(exc) is True


@pytest.mark.parametrize("exc", [
    ValueError("bad input"),
    KeyError("missing"),
    Exception("invalid argument"),
    Exception("permission denied"),
])
def test_is_transient_returns_false(exc):
    assert _to._is_transient_error(exc) is False


# ── DB helpers ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def tenant_with_employee_and_task(db: AsyncSession):
    """Create one tenant + AIEmployee + Task addressed to that employee."""
    tenant = Tenant(id=uuid.uuid4(), name="T", nif="A1", plan="starter")
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid.uuid4(), tenant_id=tenant.id, email="t@t.com",
        hashed_password="x", full_name="Tester", role="admin",
    )
    db.add(user)

    employee = AIEmployee(
        id=uuid.uuid4(), tenant_id=tenant.id, name="Ana", role="Billing",
        domain="billing", system_prompt="x", budget_limit_usd=10, status="idle",
    )
    db.add(employee)
    await db.flush()

    task = Task(
        id=uuid.uuid4(), tenant_id=tenant.id, created_by=user.id,
        domain="billing", user_intent="Lista facturas", status="pending",
        additional_metadata={"addressed_employee_id": str(employee.id)},
    )
    db.add(task)
    await db.commit()
    return tenant, employee, task


@pytest.mark.asyncio
async def test_set_agent_status_updates_employee(db, tenant_with_employee_and_task):
    tenant, employee, _ = tenant_with_employee_and_task
    await _to._set_agent_status(db, str(employee.id), str(tenant.id), "working")
    await db.commit()
    fresh = await db.execute(select(AIEmployee).where(AIEmployee.id == employee.id))
    assert fresh.scalar_one().status == "working"


@pytest.mark.asyncio
async def test_set_agent_status_silent_for_unknown_employee(db):
    """Should not raise if the employee doesn't exist."""
    await _to._set_agent_status(db, str(uuid.uuid4()), str(uuid.uuid4()), "idle")


@pytest.mark.asyncio
async def test_save_final_state_persists_status_and_results(db, tenant_with_employee_and_task):
    _, _, task = tenant_with_employee_and_task
    final = {
        "status": "done",
        "plan": [{"step": 1}],
        "agent_results": [{"agent": "billing", "output": "ok"}],
        "current_step": 1,
        "requires_human_approval": False,
        "error_message": None,
    }
    await _state._save_final_state(task, final, db)
    await db.commit()

    fresh = await db.execute(select(Task).where(Task.id == task.id))
    t = fresh.scalar_one()
    assert t.status == "done"
    assert t.completed_at is not None
    assert t.agent_results == [{"agent": "billing", "output": "ok"}]


@pytest.mark.asyncio
async def test_save_final_state_sets_completed_only_for_terminal_states(db, tenant_with_employee_and_task):
    _, _, task = tenant_with_employee_and_task
    await _state._save_final_state(
        task,
        {"status": "awaiting_approval", "plan": None, "agent_results": [], "current_step": 0,
         "requires_human_approval": True, "error_message": None},
        db,
    )
    await db.commit()
    fresh = await db.execute(select(Task).where(Task.id == task.id))
    t = fresh.scalar_one()
    assert t.status == "awaiting_approval"
    assert t.completed_at is None


@pytest.mark.asyncio
async def test_mark_task_failed_writes_error(tenant_with_employee_and_task):
    _, _, task = tenant_with_employee_and_task
    await _state._mark_task_failed(str(task.id), "boom: something broke")

    # _mark_task_failed opens its own AsyncSessionLocal — read via fresh session
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as fresh_db:
        t = (await fresh_db.execute(select(Task).where(Task.id == task.id))).scalar_one()
        assert t.status == "failed"
        assert "boom" in (t.error_message or "")
        assert t.completed_at is not None


@pytest.mark.asyncio
async def test_log_task_completion_creates_activity(db, tenant_with_employee_and_task):
    tenant, employee, task = tenant_with_employee_and_task
    final_state = {
        "agent_results": [{"agent": "billing", "summary": "Listadas 5 facturas"}],
        "error_message": None,
    }
    entry = await _to._log_task_completion(
        db, task, final_state, str(employee.id), str(tenant.id)
    )
    await db.commit()
    assert entry is not None
    assert "Listadas 5 facturas" in entry.message
    assert entry.icon == "✅"


@pytest.mark.asyncio
async def test_log_task_completion_marks_error_with_x(db, tenant_with_employee_and_task):
    tenant, employee, task = tenant_with_employee_and_task
    final_state = {"agent_results": [], "error_message": "tool failed: 429"}
    entry = await _to._log_task_completion(
        db, task, final_state, str(employee.id), str(tenant.id)
    )
    await db.commit()
    assert entry.icon == "❌"
    assert "tool failed" in entry.message


# ── End-to-end with _stream_and_log mocked ───────────────────────────────────

class _FakeUsageCallback:
    """Stand-in for UsageTrackingCallback with controllable token totals."""
    def __init__(self, tokens_in=0, tokens_out=0, cost_usd=0.0, provider="anthropic"):
        self.total_tokens_in = tokens_in
        self.total_tokens_out = tokens_out
        self.total_cost_usd = cost_usd
        self._current_provider = provider


@pytest.mark.asyncio
async def test_execute_orchestrator_writes_token_ledger_for_employee_task(
    tenant_with_employee_and_task,
):
    tenant, employee, task = tenant_with_employee_and_task

    fake_final_state = {
        "status": "done",
        "plan": None,
        "agent_results": [{"agent": "billing", "summary": "ok"}],
        "current_step": 1,
        "requires_human_approval": False,
        "error_message": None,
    }
    fake_callback = _FakeUsageCallback(
        tokens_in=1500, tokens_out=400, cost_usd=0.012, provider="anthropic"
    )

    async def fake_stream_and_log(task_id, initial_state, orchestrator):
        return fake_final_state, fake_callback

    with patch.object(_to, "_stream_and_log", new=fake_stream_and_log), \
         patch("app.services.workflow.activity.log_activity", new=AsyncMock(return_value=None)):
        await _to._execute_orchestrator(str(task.id))

    # Re-fetch via a fresh session to avoid the test fixture's stale view
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as fresh_db:
        ledger_rows = (await fresh_db.execute(
            select(TokenLedger).where(TokenLedger.employee_id == employee.id)
        )).scalars().all()
        assert len(ledger_rows) == 1
        row = ledger_rows[0]
        assert row.prompt_tokens == 1500
        assert row.completion_tokens == 400
        assert float(row.cost_usd) == pytest.approx(0.012, abs=1e-6)
        assert row.llm_provider == "anthropic"
        assert row.tenant_id == tenant.id

        # Employee status must end as "idle" (started at "idle" → working → idle)
        emp_fresh = (await fresh_db.execute(
            select(AIEmployee).where(AIEmployee.id == employee.id)
        )).scalar_one()
        assert emp_fresh.status == "idle"

        # Task must be persisted as "done"
        task_fresh = (await fresh_db.execute(
            select(Task).where(Task.id == task.id)
        )).scalar_one()
        assert task_fresh.status == "done"


@pytest.mark.asyncio
async def test_execute_orchestrator_skips_cancelled_task(db, tenant_with_employee_and_task):
    _, _, task = tenant_with_employee_and_task
    task.status = "cancelled"
    await db.commit()

    async def must_not_be_called(*a, **kw):
        raise AssertionError("LangGraph stream should not run for cancelled task")

    with patch.object(_to, "_stream_and_log", new=must_not_be_called):
        await _to._execute_orchestrator(str(task.id))

    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as fresh_db:
        t = (await fresh_db.execute(select(Task).where(Task.id == task.id))).scalar_one()
        assert t.status == "cancelled"  # untouched
