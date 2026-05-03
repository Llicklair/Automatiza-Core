"""Backward-compatibility shim — implementation in queries.py / commands.py."""
from app.services.sales.commands import convert_to_invoice, create_quote, delete_quote, update_quote
from app.services.sales.queries import get_quote, list_quotes

__all__ = ["list_quotes", "get_quote", "create_quote", "update_quote", "delete_quote", "convert_to_invoice"]
