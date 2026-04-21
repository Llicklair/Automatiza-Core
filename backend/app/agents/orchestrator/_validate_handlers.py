"""Node handlers: validate_node."""

import asyncio
import logging

from app.agents.orchestrator.state import VALID_DOMAINS, OrchestratorState, TaskStatus
from app.services.llm_cache import llm_cache

logger = logging.getLogger(__name__)


async def validate_node(state: OrchestratorState) -> OrchestratorState:
    """
    Validación determinista pre-ejecución.
    Verifica que el plan es ejecutable antes de invocar ningún agente o LLM.
    """
    plan = state.get("plan", [])
    if not plan:
        return {
            **state,
            "status": TaskStatus.FAILED,
            "error_message": "El plan está vacío tras la fase de planificación",
        }

    # Fail fast: agentes inválidos no deben llegar a dispatch
    invalid = [
        s["id"]
        for s in plan
        if s.get("agent") not in VALID_DOMAINS and s.get("agent") != "node_engine"
    ]
    if invalid:
        # Invalidar cache envenenado para que el próximo intento regenere el plan
        try:
            _tenant_id = state.get("tenant_id", "")
            _cache_key = f"plan:{state['user_intent']}"
            asyncio.create_task(llm_cache.invalidate(_tenant_id, _cache_key))
        except Exception as _e:
            logger.warning("Error invalidando caché de plan envenenado: %s", _e)
        return {
            **state,
            "status": TaskStatus.FAILED,
            "error_message": f"Plan contiene agentes no reconocidos: {invalid}",
        }

    return {
        **state,
        "status": TaskStatus.EXECUTING,
        "iteration_count": state["iteration_count"] + 1,
    }
