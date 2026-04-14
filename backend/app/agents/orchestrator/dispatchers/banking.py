"""
Dispatcher bancario (banking agent).
Invoca el banking agent autónomo (LangGraph).
"""

import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState

logger = logging.getLogger(__name__)


async def _dispatch_banking(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente bancario autónomo via LangGraph."""
    from app.agents.banking import graph
    from app.agents.orchestrator.dispatchers.misc import _run_graph_agent

    return await _run_graph_agent(graph, state, subtask, "banking", "bancos")
