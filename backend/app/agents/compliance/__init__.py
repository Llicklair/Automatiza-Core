"""Compliance agent package.

Public API: the compiled ``graph`` plus the individual ``@tool`` functions
consumed by ``app.agents.tool_registry``. Internal nodes, the uncompiled
workflow and the system prompt are intentionally NOT re-exported (CLAUDE.md
agent boundary).
"""

from .agent import graph
from .tools import (
    check_boe_news,
    check_fiscal_deadlines,
    check_quarter_preventive,
    fiscal_query,
)

__all__ = [
    "graph",
    "check_fiscal_deadlines",
    "check_boe_news",
    "check_quarter_preventive",
    "fiscal_query",
]
