"""Tests del wrapper de métricas en _invoke_dispatcher.

Valida que:
- AgentResult con success=True → status "success"
- AgentResult con success=False → status "failed"
- asyncio.TimeoutError → status "timeout" y la excepción se re-lanza
- Cualquier otra excepción → status "error" y se re-lanza
"""

import asyncio
from unittest.mock import patch

import pytest
from app.agents.orchestrator import _dispatch_handlers


@pytest.fixture
def captured_runs():
    """Captura cada llamada a record_agent_run en una lista para inspección."""
    runs: list[tuple[str, str, float]] = []

    def fake_record(agent: str, status: str, duration: float) -> None:
        runs.append((agent, status, duration))

    with patch(
        "app.core.observability.record_agent_run", side_effect=fake_record
    ):
        yield runs


async def test_records_success_when_result_success_true(captured_runs, monkeypatch):
    async def fake_impl(state, subtask, agent):
        return {"subtask_id": "x", "agent": agent, "success": True, "output": {}, "error": None}

    monkeypatch.setattr(_dispatch_handlers, "_invoke_dispatcher_impl", fake_impl)

    await _dispatch_handlers._invoke_dispatcher({"tenant_id": "t"}, {"id": "x"}, "billing")

    assert len(captured_runs) == 1
    agent, status, duration = captured_runs[0]
    assert agent == "billing"
    assert status == "success"
    assert duration >= 0


async def test_records_failed_when_result_success_false(captured_runs, monkeypatch):
    async def fake_impl(state, subtask, agent):
        return {"subtask_id": "x", "agent": agent, "success": False, "output": {}, "error": "fail"}

    monkeypatch.setattr(_dispatch_handlers, "_invoke_dispatcher_impl", fake_impl)

    await _dispatch_handlers._invoke_dispatcher({"tenant_id": "t"}, {"id": "x"}, "hr")

    assert captured_runs[0][1] == "failed"


async def test_records_timeout_and_reraises(captured_runs, monkeypatch):
    async def fake_impl(state, subtask, agent):
        raise TimeoutError()

    monkeypatch.setattr(_dispatch_handlers, "_invoke_dispatcher_impl", fake_impl)

    with pytest.raises(asyncio.TimeoutError):
        await _dispatch_handlers._invoke_dispatcher({"tenant_id": "t"}, {"id": "x"}, "documents")

    assert captured_runs[0][1] == "timeout"


async def test_records_error_and_reraises(captured_runs, monkeypatch):
    async def fake_impl(state, subtask, agent):
        raise RuntimeError("boom")

    monkeypatch.setattr(_dispatch_handlers, "_invoke_dispatcher_impl", fake_impl)

    with pytest.raises(RuntimeError, match="boom"):
        await _dispatch_handlers._invoke_dispatcher({"tenant_id": "t"}, {"id": "x"}, "email")

    # Sin manejo explícito, el status default "error" persiste.
    assert captured_runs[0][1] == "error"
