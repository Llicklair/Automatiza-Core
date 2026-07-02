"""Backward-compatibility shim — implementation in queries.py / commands.py."""

from app.services.billing.commands import (
    create_fixed_asset,
    create_journal_entry,
    delete_fixed_asset,
    delete_journal_entry,
    update_fixed_asset,
)
from app.services.billing.queries import (
    list_fixed_assets,
    list_journal_entries,
)

__all__ = [
    "list_journal_entries",
    "create_journal_entry",
    "delete_journal_entry",
    "list_fixed_assets",
    "create_fixed_asset",
    "update_fixed_asset",
    "delete_fixed_asset",
]
