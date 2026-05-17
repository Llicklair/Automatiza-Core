"""Excel agent package.

Public API: the compiled ``graph`` plus the individual ``@tool`` functions
consumed by ``app.agents.tool_registry``. The internal ``tools`` list is
intentionally NOT re-exported (CLAUDE.md agent boundary).
"""

from .agent import graph
from .tools import (
    export_erp_data,
    import_excel,
    list_available_datasets,
    modify_excel,
    read_excel,
)

__all__ = [
    "graph",
    "export_erp_data",
    "import_excel",
    "list_available_datasets",
    "modify_excel",
    "read_excel",
]
