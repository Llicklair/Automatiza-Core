"""
Dispatcher de Recursos Humanos (HR agent).
Invoca el HR agent autónomo (LangGraph).
"""
import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState

logger = logging.getLogger(__name__)


async def _dispatch_hr(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de RRHH autónomo via LangGraph."""
    from app.agents.hr_agent import graph
    from app.agents.orchestrator.dispatchers.misc import _run_graph_agent

    return await _run_graph_agent(graph, state, subtask, "hr", "nominas")
