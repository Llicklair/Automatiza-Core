"""Backward-compatibility shim — implementation in queries.py / commands.py."""
from app.services.billing.commands import (
    create_invoice,
    create_rectificativa,
    delete_invoice,
    generate_and_save_invoice_pdf,
    update_status,
)
from app.services.billing.queries import (
    UPLOAD_DIR,
    VALID_IVA,
    _build_invoice_data,
    _load_invoice,
    _load_tenant,
    build_invoice_pdf,
    build_rectificative_pdf,
    build_retention_pdf,
    get_invoice,
    list_invoices,
)

__all__ = [
    "list_invoices",
    "get_invoice",
    "create_invoice",
    "create_rectificativa",
    "update_status",
    "delete_invoice",
    "generate_and_save_invoice_pdf",
    "build_invoice_pdf",
    "build_rectificative_pdf",
    "build_retention_pdf",
    "_load_invoice",
    "_load_tenant",
    "_build_invoice_data",
    "UPLOAD_DIR",
    "VALID_IVA",
]
