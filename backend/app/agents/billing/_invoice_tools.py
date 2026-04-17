"""
Invoice tools — re-export facade.

Logic lives in sub-modules:
  _invoice_pdf_tools.py     — PDF generation and template helpers
  _invoice_create_async.py  — heavy invoice creation logic
  _invoice_write_tools.py   — create / update_status / update tools (@tool)
  _invoice_query_tools.py   — list / send_by_email tools (@tool)
"""

from ._invoice_create_async import _create_invoice_async
from ._invoice_pdf_tools import (
    _generate_and_save_invoice_pdf,
    _load_invoice_template,
)
from ._invoice_query_tools import (
    _list_invoices_async,
    _send_invoice_by_email_async,
    list_invoices,
    send_invoice_by_email,
)
from ._invoice_write_tools import (
    _update_invoice_async,
    _update_invoice_status_async,
    create_invoice,
    update_invoice,
    update_invoice_status,
)

__all__ = [
    # @tool public
    "create_invoice",
    "list_invoices",
    "update_invoice_status",
    "update_invoice",
    "send_invoice_by_email",
    # private helpers (used by sub-modules / tests)
    "_create_invoice_async",
    "_list_invoices_async",
    "_update_invoice_status_async",
    "_update_invoice_async",
    "_send_invoice_by_email_async",
    "_load_invoice_template",
    "_generate_and_save_invoice_pdf",
]
