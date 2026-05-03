"""Backward-compatibility shim — implementation in queries.py / commands.py."""
from app.services.sales.commands import create_purchase_order, delete_purchase_order, update_purchase_order
from app.services.sales.queries import list_purchase_orders

__all__ = ["list_purchase_orders", "create_purchase_order", "update_purchase_order", "delete_purchase_order"]
