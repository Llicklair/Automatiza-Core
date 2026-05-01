"""
Excel agent tool definitions — re-export facade.

All logic lives in the sub-modules:
  _fetchers.py      — DB fetchers, _FETCHER_MAP, _detect_datasets
  _writer.py        — _write_excel, _hex_to_lighter
  _export_tools.py  — export_erp_data, list_available_datasets
  _import_tools.py  — import_excel + import helpers
  _modify_tools.py  — modify_excel, read_excel
"""

import os

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge

from ._export_tools import export_erp_data, list_available_datasets
from ._import_tools import import_excel
from ._modify_tools import modify_excel, read_excel

UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))
os.makedirs(UPLOADS_DIR, exist_ok=True)

__all__ = [
    "export_erp_data",
    "list_available_datasets",
    "import_excel",
    "modify_excel",
    "read_excel",
]

# ─── Lista de herramientas (exportada para agent.py) ─────────────────────────

tools = [
    export_erp_data,
    list_available_datasets,
    import_excel,
    modify_excel,
    read_excel,
    create_document,
    list_tenant_documents,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
]


# Defensa multi-tenant: envolver tools para forzar tenant_id del ContextVar
from app.agents.tenant_context import isolated as _isolated
tools = _isolated(tools)
