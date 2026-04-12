"""
Billing agent package.

Re-exports all public symbols for backward compatibility with
``from app.agents.billing_agent import ...`` style imports.
"""

from .agent import (
    billing_agent_node,
    billing_finalize_node,
    graph,
    workflow,
)
from .prompts import BILLING_SYSTEM_PROMPT
from .tools import (
    create_albaran,
    create_invoice,
    list_albaranes,
    list_invoices,
    search_client,
    send_invoice_by_email,
    tools,
    update_invoice,
    update_invoice_status,
)

__all__ = [
    # Agent graph
    "graph",
    "workflow",
    "billing_agent_node",
    "billing_finalize_node",
    "BILLING_SYSTEM_PROMPT",
    # Tools
    "tools",
    "create_invoice",
    "list_invoices",
    "search_client",
    "update_invoice_status",
    "update_invoice",
    "send_invoice_by_email",
    "list_albaranes",
    "create_albaran",
]
