"""Dispatcher contable (accounting agent)."""

import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState

logger = logging.getLogger(__name__)


async def _dispatch_accounting(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de contabilidad autónomo via LangGraph."""
    from app.agents.accounting import graph
    from app.agents.orchestrator.dispatchers.misc import _run_graph_agent

    return await _run_graph_agent(graph, state, subtask, "accounting", "contabilidad")
