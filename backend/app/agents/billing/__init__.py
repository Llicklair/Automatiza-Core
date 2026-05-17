"""Billing agent package.

Public API: the compiled ``graph`` plus the individual ``@tool`` functions
consumed by ``app.agents.tool_registry``. Internal nodes, the uncompiled
workflow and the system prompt are intentionally NOT re-exported (CLAUDE.md
agent boundary).
"""

from .agent import graph
from .tools import (
    create_invoice,
    list_invoices,
    search_client,
    send_invoice_by_email,
    update_invoice,
    update_invoice_status,
)

__all__ = [
    "graph",
    "create_invoice",
    "list_invoices",
    "search_client",
    "update_invoice_status",
    "update_invoice",
    "send_invoice_by_email",
]
