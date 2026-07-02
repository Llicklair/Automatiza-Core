"""Backward-compatibility shim — implementation in queries.py / commands.py."""

from app.services.sales.commands import create_client, delete_client, update_client
from app.services.sales.queries import list_client_invoices, list_clients

__all__ = ["list_clients", "list_client_invoices", "create_client", "update_client", "delete_client"]
