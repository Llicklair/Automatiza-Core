"""
Billing agent tool definitions — re-export facade.

All logic lives in the sub-modules:
  _client_tools.py   — search_client, _resolve_client
  _invoice_tools.py  — create/list/update/send invoice tools
  _albaran_tools.py  — list/create albaranes
"""

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
    update_existing_document,
)
from app.agents.agent_tools.knowledge import (
    delete_tenant_knowledge,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
)

from ._albaran_tools import create_albaran, list_albaranes
from ._client_tools import (  # noqa: F401 (_resolve_client used by sub-modules)
    _resolve_client,
    search_client,
)
from ._invoice_tools import (
    create_invoice,
    list_invoices,
    send_invoice_by_email,
    update_invoice,
    update_invoice_status,
)

__all__ = [
    "create_invoice",
    "list_invoices",
    "search_client",
    "update_invoice_status",
    "update_invoice",
    "send_invoice_by_email",
    "list_albaranes",
    "create_albaran",
]

# ─── Lista de herramientas ────────────────────────────────────────────────────

tools = [
    create_invoice,
    list_invoices,
    search_client,
    update_invoice_status,
    update_invoice,
    send_invoice_by_email,
    list_albaranes,
    create_albaran,
    create_document,
    list_tenant_documents,
    update_existing_document,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
    delete_tenant_knowledge,
]
