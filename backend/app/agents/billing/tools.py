"""
Billing agent tool definitions — re-export facade.

All logic lives in the sub-modules:
  _client_tools.py   — _resolve_client (private helper for invoice creation)
  _invoice_tools.py  — create/list/update/send invoice tools
  _albaran_tools.py  — list/create albaranes

Cross-domain tools (used by both billing and CRM) live in app.agents.agent_tools.*
"""

from app.agents.agent_tools.clients import search_client
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
from app.agents.agent_tools.reports import create_pdf_report, create_pdf_text_report

from ._albaran_tools import create_albaran, list_albaranes
from ._client_tools import _resolve_client  # noqa: F401 (used by sub-modules)
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
    create_pdf_report,
    create_pdf_text_report,
]


# Defensa multi-tenant: envolver tools para forzar tenant_id del ContextVar
from app.agents.tenant_context import isolated as _isolated

tools = _isolated(tools)
