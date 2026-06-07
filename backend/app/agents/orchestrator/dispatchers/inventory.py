"""Dispatcher para el agente de stock (inventario)."""

from app.agents.orchestrator.dispatchers.misc import _run_graph_agent
from app.agents.orchestrator.state import AgentResult, OrchestratorState


async def _dispatch_inventory(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de stock/inventario."""
    from app.agents.inventory import graph

    return await _run_graph_agent(graph, state, subtask, "inventory", "inventario")
