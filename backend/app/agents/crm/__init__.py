"""
CRM agent package.
"""

from .agent import crm_agent_node, crm_finalize_node, graph, workflow
from .tools import (
    create_client,
    create_opportunity,
    list_opportunities,
    qualify_leads,
    tools,
    update_opportunity_stage,
)

__all__ = [
    "graph",
    "workflow",
    "crm_agent_node",
    "crm_finalize_node",
    "tools",
    "list_opportunities",
    "create_opportunity",
    "update_opportunity_stage",
    "qualify_leads",
    "create_client",
]
