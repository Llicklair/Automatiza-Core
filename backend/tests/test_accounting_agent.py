"""Tests for the accounting agent: graph structure, tools, and node logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage


# ── Graph structure ───────────────────────────────────────────────────────────

def test_graph_compiles():
    from app.agents.accounting.agent import graph
    assert graph is not None


def test_graph_has_expected_nodes():
    from app.agents.accounting.agent import graph
    node_names = set(graph.nodes.keys())
    assert "accounting_agent" in node_names
    assert "tools" in node_names
    assert "finalize" in node_names


def test_graph_entry_point():
    from app.agents.accounting.agent import graph
    # LangGraph compiled graphs expose their nodes — verify the entry node exists
    assert "accounting_agent" in graph.nodes


# ── Tools registration ────────────────────────────────────────────────────────

def test_five_tools_registered():
    from app.agents.accounting.agent import tools
    assert len(tools) == 5


def test_tool_names():
    from app.agents.accounting.agent import tools
    names = {t.name for t in tools}
    assert "create_journal_entry" in names
    assert "list_journal_entries" in names
    assert "get_account_balance" in names
    assert "get_profit_loss_summary" in names
    assert "list_fixed_assets" in names


def test_tools_have_docstrings():
    from app.agents.accounting.agent import tools
    for t in tools:
        assert t.description, f"Tool {t.name} missing description"


# ── accounting_finalize_node (pure Python, no DB) ────────────────────────────

def test_finalize_node_extracts_last_message_content():
    from app.agents.accounting.agent import accounting_finalize_node

    state = {
        "messages": [HumanMessage(content="hola"), AIMessage(content="El asiento fue creado.")],
        "agent_results": [],
        "tenant_id": "test-tenant",
        "user_intent": "crea asiento",
        "status": "running",
    }
    result = accounting_finalize_node(state)

    assert result["status"] == "done"
    assert len(result["agent_results"]) == 1
    step = result["agent_results"][0]
    assert step["action_taken"] == "El asiento fue creado."


def test_finalize_node_handles_non_string_content():
    from app.agents.accounting.agent import accounting_finalize_node

    last_msg = AIMessage(content=[{"type": "text", "text": "done"}])
    state = {
        "messages": [last_msg],
        "agent_results": [],
        "tenant_id": "test-tenant",
        "user_intent": "lista activos",
        "status": "running",
    }
    result = accounting_finalize_node(state)

    assert result["status"] == "done"
    assert result["agent_results"][0]["action_taken"] == "Operación contable completada."


# ── accounting_agent_node with mocked LLM ────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_node_builds_initial_messages():
    from app.agents.accounting.agent import accounting_agent_node

    ai_response = AIMessage(content="No se requieren herramientas.", tool_calls=[])

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(return_value=ai_response)

    state = {
        "messages": [],
        "agent_results": [],
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "user_intent": "¿Cuánto es el saldo de la cuenta 430?",
        "status": "running",
    }

    with patch("app.agents.accounting.agent.get_llm", return_value=mock_llm):
        result = await accounting_agent_node(state)

    messages = result["messages"]
    # SystemMessage + HumanMessage + AIMessage
    assert len(messages) == 3
    assert messages[1].content == "¿Cuánto es el saldo de la cuenta 430?"
    assert messages[2] is ai_response


@pytest.mark.asyncio
async def test_agent_node_continues_existing_messages():
    from app.agents.accounting.agent import accounting_agent_node

    existing_msgs = [
        HumanMessage(content="primera consulta"),
        AIMessage(content="respuesta previa"),
    ]
    ai_response = AIMessage(content="continuando", tool_calls=[])

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(return_value=ai_response)

    state = {
        "messages": list(existing_msgs),
        "agent_results": [],
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "user_intent": "segunda consulta",
        "status": "running",
    }

    with patch("app.agents.accounting.agent.get_llm", return_value=mock_llm):
        result = await accounting_agent_node(state)

    # When messages already exist, no extra messages are prepended
    assert result["messages"][-1] is ai_response


@pytest.mark.asyncio
async def test_agent_node_accumulates_agent_results():
    from app.agents.accounting.agent import accounting_agent_node

    ai_response = AIMessage(content="ok", tool_calls=[])

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(return_value=ai_response)

    existing_result = {"step_id": "prev", "description": "paso anterior", "status": "completed", "action_taken": "x"}

    state = {
        "messages": [],
        "agent_results": [existing_result],
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "user_intent": "consulta",
        "status": "running",
    }

    with patch("app.agents.accounting.agent.get_llm", return_value=mock_llm):
        result = await accounting_agent_node(state)

    assert len(result["agent_results"]) == 2
