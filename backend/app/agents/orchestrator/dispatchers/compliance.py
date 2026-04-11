"""
Dispatcher de compliance fiscal.
Invoca el compliance agent autónomo (LangGraph).
"""

import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState

logger = logging.getLogger(__name__)


async def _dispatch_compliance(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de compliance fiscal autónomo via LangGraph."""
    from app.agents.compliance_agent import graph
    from app.agents.orchestrator.dispatchers.misc import _run_graph_agent

    return await _run_graph_agent(graph, state, subtask, "compliance", "fiscal")
