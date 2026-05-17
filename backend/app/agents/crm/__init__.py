"""CRM agent package.

Public API: the compiled ``graph`` plus the individual ``@tool`` functions
consumed by ``app.agents.tool_registry``. Internal nodes, the uncompiled
workflow and helpers are intentionally NOT re-exported (CLAUDE.md agent
boundary).
"""

from .agent import graph
from .tools import (
    create_opportunity,
    list_opportunities,
    qualify_leads,
    update_opportunity_stage,
)

__all__ = [
    "graph",
    "list_opportunities",
    "create_opportunity",
    "update_opportunity_stage",
    "qualify_leads",
]
