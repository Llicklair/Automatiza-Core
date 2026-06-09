"""Marketing agent package.

Public API: the compiled ``graph`` plus the individual ``@tool`` functions
consumed by ``app.agents.tool_registry``. Internal nodes, the uncompiled
workflow and the system prompt are intentionally NOT re-exported (CLAUDE.md
agent boundary).
"""

from .agent import graph, run_agent
from .tools import get_product_catalog

__all__ = [
    "graph",
    "run_agent",
    "get_product_catalog",
]
