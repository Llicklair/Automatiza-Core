"""Dispatcher para el agente de reclutamiento autónomo."""

from app.agents.orchestrator.dispatchers.misc import _run_graph_agent
from app.agents.orchestrator.state import AgentResult, OrchestratorState


async def _dispatch_recruitment(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de reclutamiento autónomo."""
    from app.agents.recruitment import graph

    return await _run_graph_agent(graph, state, subtask, "recruitment", "reclutamiento")
