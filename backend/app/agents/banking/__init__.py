"""
Banking agent package.

Re-exports all public symbols for backward compatibility with
``from app.agents.banking_agent import ...`` style imports.
"""

from .agent import (
    BANKING_SYSTEM_PROMPT,
    banking_agent_node,
    banking_finalize_node,
    graph,
    workflow,
)
from .tools import (
    check_balances,
    financial_summary,
    list_transactions,
    reconcile_transactions,
    tools,
)

__all__ = [
    # Agent graph
    "graph",
    "workflow",
    "banking_agent_node",
    "banking_finalize_node",
    "BANKING_SYSTEM_PROMPT",
    # Tools
    "tools",
    "check_balances",
    "list_transactions",
    "financial_summary",
    "reconcile_transactions",
]
