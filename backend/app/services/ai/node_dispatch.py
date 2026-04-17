"""
node_dispatch — Agent dispatcher for NodeEngine.

Extracted from node_engine.py. Provides dispatch_agent() as a standalone
function so NodeEngine can delegate domain routing without owning that logic.
"""

from __future__ import annotations


async def dispatch_agent(domain: str, state: dict, subtask: dict) -> dict:
    """Dispatch to the appropriate agent based on domain."""
    from app.agents.orchestrator.dispatchers import (
        _dispatch_banking,
        _dispatch_billing,
        _dispatch_compliance,
        _dispatch_crm,
        _dispatch_documents,
        _dispatch_email,
        _dispatch_excel,
        _dispatch_hr,
        _dispatch_rag,
        _dispatch_skill,
        _dispatch_workflow,
    )

    dispatch_map = {
        "billing": _dispatch_billing,
        "documents": _dispatch_documents,
        "hr": _dispatch_hr,
        "email": _dispatch_email,
        "crm": _dispatch_crm,
        "banking": _dispatch_banking,
        "compliance": _dispatch_compliance,
        "rag": _dispatch_rag,
        "excel": _dispatch_excel,
        "workflow": _dispatch_workflow,
        "skill": _dispatch_skill,
    }

    try:
        lookup = domain if not domain.startswith("skill:") else "skill"
        handler = dispatch_map.get(lookup)
        if not handler:
            return {
                "subtask_id": subtask["id"],
                "agent": domain,
                "success": False,
                "output": {"message": f"Agente '{domain}' no reconocido"},
                "error": f"Unknown domain: {domain}",
            }
        return await handler(state, subtask)
    except Exception as e:
        return {
            "subtask_id": subtask["id"],
            "agent": domain,
            "success": False,
            "output": {"error": str(e)},
            "error": str(e),
        }
