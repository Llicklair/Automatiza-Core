"""
Excel agent package.

Re-exports all public symbols that were previously importable from
``app.agents.excel_agent`` so existing imports keep working.
"""

from .agent import graph  # noqa: F401
from .tools import (  # noqa: F401
    export_erp_data,
    import_excel,
    list_available_datasets,
    modify_excel,
    read_excel,
    tools,
)
