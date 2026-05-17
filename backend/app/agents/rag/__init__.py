"""RAG agent package.

Public API: the compiled ``graph`` plus the individual ``@tool`` functions
consumed by ``app.agents.tool_registry``. Internal nodes, the uncompiled
workflow and the system prompt are intentionally NOT re-exported (CLAUDE.md
agent boundary).
"""

from .agent import graph
from .tools import (
    answer_from_documents,
    search_documents,
)

__all__ = [
    "graph",
    "search_documents",
    "answer_from_documents",
]
