"""
node_dispatch — Agent dispatcher for NodeEngine.

Delega el routing al Coordinador (invoke_dispatcher) para mantener una sola
fuente de verdad: built-in DISPATCHER_MAP → skill → AIEmployee custom.
"""

from __future__ import annotations


async def dispatch_agent(domain: str, state: dict, subtask: dict) -> dict:
    """Dispatch to the appropriate agent based on domain."""
    from app.agents.orchestrator import invoke_dispatcher

    try:
        return await invoke_dispatcher(state, subtask, domain)
    except Exception as e:
        return {
            "subtask_id": subtask["id"],
            "agent": domain,
            "success": False,
            "output": {"error": str(e)},
            "error": str(e),
        }
