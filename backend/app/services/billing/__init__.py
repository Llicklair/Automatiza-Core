"""Billing domain services — re-exports for backwards compatibility."""

from app.services.billing.accounting import (
    list_journal_entries,
    create_journal_entry,
    delete_journal_entry,
    list_fixed_assets,
    create_fixed_asset,
    update_fixed_asset,
    delete_fixed_asset,
)
from app.services.billing.invoice import (
    list_invoices,
    get_invoice,
    create_invoice,
    update_status,
    delete_invoice,
    generate_and_save_invoice_pdf,
    build_invoice_pdf,
    build_rectificative_pdf,
    build_retention_pdf,
)

__all__ = [
    # accounting
    "list_journal_entries",
    "create_journal_entry",
    "delete_journal_entry",
    "list_fixed_assets",
    "create_fixed_asset",
    "update_fixed_asset",
    "delete_fixed_asset",
    # invoice
    "list_invoices",
    "get_invoice",
    "create_invoice",
    "update_status",
    "delete_invoice",
    "generate_and_save_invoice_pdf",
    "build_invoice_pdf",
    "build_rectificative_pdf",
    "build_retention_pdf",
]
