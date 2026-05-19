"""Smoke tests for the crm agent: graph, tools, and node logic."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage


# ── Graph structure ───────────────────────────────────────────────────────────

def test_graph_compiles():
    from app.agents.crm.agent import graph
    assert graph is not None


def test_graph_has_expected_nodes():
    from app.agents.crm.agent import graph
    node_names = set(graph.nodes.keys())
    assert "crm_agent" in node_names
    assert "tools" in node_names
    assert "finalize" in node_names


# ── Tools registration ────────────────────────────────────────────────────────

def test_tools_not_empty():
    from app.agents.crm.agent import tools
    assert len(tools) > 0


def test_tools_have_docstrings():
    from app.agents.crm.agent import tools
    for t in tools:
        assert t.description, f"Tool {t.name} missing description"


def test_core_crm_tools_registered():
    from app.agents.crm.agent import tools
    names = {t.name for t in tools}
    expected = {
        "list_opportunities",
        "create_opportunity",
        "update_opportunity_stage",
        "qualify_leads",
        "create_client",
    }
    missing = expected - names
    assert not missing, f"Missing CRM tools: {missing}"


# ── Node behaviour with mocked LLM ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crm_agent_node_invokes_llm():
    from app.agents.crm.agent import crm_agent_node

    ai_response = AIMessage(content="Oportunidades listadas.", tool_calls=[])

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(return_value=ai_response)

    state = {
        "messages": [],
        "agent_results": [],
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "user_intent": "Lista las oportunidades abiertas",
        "status": "running",
    }

    with patch("app.agents.crm.agent.get_llm", return_value=mock_llm):
        result = await crm_agent_node(state)

    assert "messages" in result
    assert result["messages"][-1] is ai_response
