"""Billing domain services — re-exports for backwards compatibility."""

from app.services.billing.commands import (
    create_fixed_asset,
    create_invoice,
    create_journal_entry,
    create_recurring,
    delete_fixed_asset,
    delete_invoice,
    delete_journal_entry,
    delete_recurring,
    generate_and_save_invoice_pdf,
    run_recurring,
    update_fixed_asset,
    update_recurring,
    update_status,
)
from app.services.billing.queries import (
    build_invoice_pdf,
    build_rectificative_pdf,
    build_retention_pdf,
    get_invoice,
    list_fixed_assets,
    list_invoices,
    list_journal_entries,
    list_recurring,
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
    # recurring
    "list_recurring",
    "create_recurring",
    "update_recurring",
    "delete_recurring",
    "run_recurring",
]
