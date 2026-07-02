"""Backward-compatibility shim — implementation in queries.py / commands.py."""

from app.services.sales.commands import (
    create_product,
    create_stock_movement,
    delete_product,
    update_product,
)
from app.services.sales.queries import (
    get_product_by_barcode,
    get_stock_valuation,
    list_products,
    list_stock_movements,
)

__all__ = [
    "list_products",
    "list_stock_movements",
    "get_product_by_barcode",
    "get_stock_valuation",
    "create_product",
    "update_product",
    "delete_product",
    "create_stock_movement",
]
