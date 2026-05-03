"""Backward-compatibility shim — implementation in queries.py / commands.py."""
from app.services.sales.commands import create_sales_order, delete_sales_order, update_sales_order
from app.services.sales.queries import list_sales_orders

__all__ = ["list_sales_orders", "create_sales_order", "update_sales_order", "delete_sales_order"]
