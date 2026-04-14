"""
Marketing agent package.
"""

from .agent import (
    MARKETING_SYSTEM_PROMPT,
    graph,
    marketing_agent_node,
    marketing_finalize_node,
    workflow,
)
from .tools import get_product_catalog, tools

__all__ = [
    "graph",
    "workflow",
    "marketing_agent_node",
    "marketing_finalize_node",
    "MARKETING_SYSTEM_PROMPT",
    "tools",
    "get_product_catalog",
]
