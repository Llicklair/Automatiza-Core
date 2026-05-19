"""Smoke tests for the banking agent: graph, tools, and node logic."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage


# ── Graph structure ───────────────────────────────────────────────────────────

def test_graph_compiles():
    from app.agents.banking.agent import graph
    assert graph is not None


def test_graph_has_expected_nodes():
    from app.agents.banking.agent import graph
    node_names = set(graph.nodes.keys())
    assert "banking_agent" in node_names
    assert "tools" in node_names
    assert "finalize" in node_names


# ── Tools registration ────────────────────────────────────────────────────────

def test_tools_not_empty():
    from app.agents.banking.agent import tools
    assert len(tools) > 0


def test_tools_have_docstrings():
    from app.agents.banking.agent import tools
    for t in tools:
        assert t.description, f"Tool {t.name} missing description"


def test_core_banking_tools_registered():
    from app.agents.banking.agent import tools
    names = {t.name for t in tools}
    expected = {
        "check_balances",
        "list_transactions",
        "reconcile_transactions",
        "financial_summary",
    }
    missing = expected - names
    assert not missing, f"Missing banking tools: {missing}"


# ── Node behaviour with mocked LLM ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_banking_agent_node_invokes_llm():
    from app.agents.banking.agent import banking_agent_node

    ai_response = AIMessage(content="Saldos consultados.", tool_calls=[])

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(return_value=ai_response)

    state = {
        "messages": [],
        "agent_results": [],
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "user_intent": "¿Cuál es el saldo de mis cuentas bancarias?",
        "status": "running",
    }

    with patch("app.agents.banking.agent.get_llm", return_value=mock_llm):
        result = await banking_agent_node(state)

    assert "messages" in result
    assert result["messages"][-1] is ai_response
