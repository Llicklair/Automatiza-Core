"""Backward-compatibility shim — implementation in queries.py / commands.py."""

from app.services.sales.commands import (
    create_albaran,
    delete_albaran,
    facturar_albaranes,
    update_albaran,
    update_albaran_status,
)
from app.services.sales.queries import get_albaran, get_albaran_pdf_data, list_albaranes

__all__ = [
    "list_albaranes",
    "get_albaran",
    "get_albaran_pdf_data",
    "create_albaran",
    "facturar_albaranes",
    "update_albaran",
    "update_albaran_status",
    "delete_albaran",
]
