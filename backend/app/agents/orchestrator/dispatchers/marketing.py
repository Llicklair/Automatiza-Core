"""Dispatcher para el agente de marketing autónomo."""

from app.agents.orchestrator.dispatchers.misc import _run_graph_agent
from app.agents.orchestrator.state import AgentResult, OrchestratorState


async def _dispatch_marketing(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de marketing autónomo."""
    from app.agents.marketing import graph

    return await _run_graph_agent(graph, state, subtask, "marketing", "marketing")
