"""Smoke tests for the marketing agent: graph, tools, and node logic."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage


# ── Graph structure ───────────────────────────────────────────────────────────

def test_graph_compiles():
    from app.agents.marketing.agent import graph
    assert graph is not None


def test_graph_has_expected_nodes():
    from app.agents.marketing.agent import graph
    node_names = set(graph.nodes.keys())
    # marketing uses "agent" as the LLM node name (not "marketing_agent")
    assert "agent" in node_names
    assert "tools" in node_names
    assert "finalize" in node_names


# ── Tools registration ────────────────────────────────────────────────────────

def test_tools_not_empty():
    from app.agents.marketing.agent import tools
    assert len(tools) > 0


def test_tools_have_docstrings():
    from app.agents.marketing.agent import tools
    for t in tools:
        assert t.description, f"Tool {t.name} missing description"


def test_core_marketing_tools_registered():
    from app.agents.marketing.agent import tools
    names = {t.name for t in tools}
    # marketing is intentionally small: catalog + PDF rendering
    expected = {"get_product_catalog", "create_pdf_report", "create_pdf_text_report"}
    missing = expected - names
    assert not missing, f"Missing marketing tools: {missing}"


# ── Node behaviour with mocked LLM ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_marketing_agent_node_invokes_llm():
    from app.agents.marketing.agent import marketing_agent_node

    ai_response = AIMessage(content="Plan de contenidos listo.", tool_calls=[])

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(return_value=ai_response)

    state = {
        "messages": [],
        "agent_results": [],
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "user_intent": "Genera un plan de marketing para este mes",
        "status": "running",
    }

    with patch("app.agents.marketing.agent.get_llm", return_value=mock_llm):
        result = await marketing_agent_node(state)

    assert "messages" in result
    assert result["messages"][-1] is ai_response
