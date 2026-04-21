"""Billing domain services — re-exports for backwards compatibility."""

from app.services.billing.accounting import (
    create_fixed_asset,
    create_journal_entry,
    delete_fixed_asset,
    delete_journal_entry,
    list_fixed_assets,
    list_journal_entries,
    update_fixed_asset,
)
from app.services.billing.invoice import (
    build_invoice_pdf,
    build_rectificative_pdf,
    build_retention_pdf,
    create_invoice,
    delete_invoice,
    generate_and_save_invoice_pdf,
    get_invoice,
    list_invoices,
    update_status,
)
from app.services.billing.recurring import (
    create_recurring,
    delete_recurring,
    list_recurring,
    run_recurring,
    update_recurring,
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
