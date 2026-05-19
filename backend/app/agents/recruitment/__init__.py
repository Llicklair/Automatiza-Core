"""Recruitment agent package.

Public API: the compiled ``graph`` plus the individual ``@tool`` functions
consumed by ``app.agents.tool_registry``. Internal nodes, the uncompiled
workflow and the system prompt are intentionally NOT re-exported (CLAUDE.md
agent boundary).
"""

from .agent import graph
from .tools import (
    create_candidate,
    create_position,
    list_candidates,
    list_positions,
    process_cv,
    update_candidate_status,
)

__all__ = [
    "graph",
    "create_position",
    "list_positions",
    "process_cv",
    "create_candidate",
    "list_candidates",
    "update_candidate_status",
]
