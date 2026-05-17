"""Banking agent package.

Public API: the compiled ``graph`` plus the individual ``@tool`` functions
consumed by ``app.agents.tool_registry``. Internal nodes, the uncompiled
workflow and the system prompt are intentionally NOT re-exported (CLAUDE.md
agent boundary).
"""

from .agent import graph
from .tools import (
    check_balances,
    financial_summary,
    list_transactions,
    reconcile_transactions,
)

__all__ = [
    "graph",
    "check_balances",
    "list_transactions",
    "financial_summary",
    "reconcile_transactions",
]
