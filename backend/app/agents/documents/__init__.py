"""Documents agent package.

Public API: the compiled ``graph`` plus the individual ``@tool`` functions
consumed by ``app.agents.tool_registry``. Internal nodes, the uncompiled
workflow and the system prompt are intentionally NOT re-exported (CLAUDE.md
agent boundary).
"""

from .agent import graph
from .tools import (
    classify_document,
    import_invoice_document,
    search_documents_semantic,
)

__all__ = [
    "graph",
    "classify_document",
    "import_invoice_document",
    "search_documents_semantic",
]
