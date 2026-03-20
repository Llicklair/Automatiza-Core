"""
Dispatcher bancario (banking agent).
Invoca el banking agent autónomo (LangGraph).
"""
import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary
from app.agents.orchestrator.helpers import _save_ai_result_as_document

logger = logging.getLogger(__name__)


async def _dispatch_banking(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente bancario autónomo via LangGraph."""
    from app.agents.banking_agent import graph
    from app.agents.orchestrator.dispatchers.misc import _run_graph_agent

    return await _run_graph_agent(graph, state, subtask, "banking", "bancos")
