"""Unit tests for llm_usage_tracker — no DB, no fixtures needed."""
import pytest
from app.services import llm_usage_tracker


@pytest.fixture(autouse=True)
def clean_tracker():
    """Flush test tenant before/after each test to avoid state leakage."""
    tid = "test-tenant-tracker"
    llm_usage_tracker.flush_tenant(tid)
    yield tid
    llm_usage_tracker.flush_tenant(tid)


def test_record_increments_calls(clean_tracker):
    tid = clean_tracker
    llm_usage_tracker.record(tid, "billing", "anthropic", 100, 50)
    stats = llm_usage_tracker.get_monthly_stats(tid, months=1)
    assert len(stats) == 1
    assert stats[0]["total_calls"] == 1
    assert stats[0]["total_tokens_in"] == 100
    assert stats[0]["total_tokens_out"] == 50


def test_record_accumulates_multiple_calls(clean_tracker):
    tid = clean_tracker
    llm_usage_tracker.record(tid, "billing", "anthropic", 100, 50)
    llm_usage_tracker.record(tid, "billing", "anthropic", 200, 80)
    stats = llm_usage_tracker.get_monthly_stats(tid, months=1)
    assert stats[0]["total_calls"] == 2
    assert stats[0]["total_tokens_in"] == 300
    assert stats[0]["total_tokens_out"] == 130


def test_record_multiple_agents(clean_tracker):
    tid = clean_tracker
    llm_usage_tracker.record(tid, "billing", "anthropic", 100, 50)
    llm_usage_tracker.record(tid, "hr", "openai", 200, 80)
    stats = llm_usage_tracker.get_monthly_stats(tid, months=1)
    agents = {a["agent"] for a in stats[0]["by_agent"]}
    assert "billing" in agents
    assert "hr" in agents


def test_estimate_cost_anthropic():
    # claude-sonnet-4-6: $3/M input, $15/M output
    cost = llm_usage_tracker.estimate_cost("anthropic", 1_000_000, 1_000_000)
    assert cost == pytest.approx(18.0, rel=0.01)


def test_estimate_cost_openai():
    cost = llm_usage_tracker.estimate_cost("openai", 1_000_000, 0)
    assert cost == pytest.approx(0.15, rel=0.01)


def test_estimate_cost_zero_for_mock():
    cost = llm_usage_tracker.estimate_cost("mock", 999_999, 999_999)
    assert cost == 0.0


def test_estimate_cost_in_stats(clean_tracker):
    tid = clean_tracker
    llm_usage_tracker.record(tid, "billing", "anthropic", 1_000_000, 0)
    stats = llm_usage_tracker.get_monthly_stats(tid, months=1)
    assert stats[0]["estimated_cost_usd"] == pytest.approx(3.0, rel=0.01)


def test_get_monthly_stats_empty(clean_tracker):
    stats = llm_usage_tracker.get_monthly_stats(clean_tracker, months=3)
    assert stats == []


def test_flush_removes_data(clean_tracker):
    tid = clean_tracker
    llm_usage_tracker.record(tid, "billing", "anthropic", 100, 50)
    llm_usage_tracker.flush_tenant(tid)
    stats = llm_usage_tracker.get_monthly_stats(tid, months=1)
    assert stats == []


def test_zero_tokens_not_recorded(clean_tracker):
    tid = clean_tracker
    llm_usage_tracker.record(tid, "billing", "anthropic", 0, 0)
    stats = llm_usage_tracker.get_monthly_stats(tid, months=1)
    assert stats == []


def test_by_agent_sorted_by_tokens(clean_tracker):
    tid = clean_tracker
    llm_usage_tracker.record(tid, "hr", "anthropic", 10, 5)
    llm_usage_tracker.record(tid, "billing", "anthropic", 1000, 500)
    stats = llm_usage_tracker.get_monthly_stats(tid, months=1)
    agents = [a["agent"] for a in stats[0]["by_agent"]]
    assert agents[0] == "billing"  # billing has more tokens → first


def test_stats_limited_to_requested_months(clean_tracker):
    stats = llm_usage_tracker.get_monthly_stats(clean_tracker, months=1)
    assert len(stats) <= 1
