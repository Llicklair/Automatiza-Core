"""Sales domain services — re-exports for backwards compatibility."""

from app.services.sales.commands import (
    convert_to_invoice,
    create_albaran,
    create_client,
    create_product,
    create_purchase_order,
    create_quote,
    create_sales_order,
    create_stock_movement,
    delete_albaran,
    delete_client,
    delete_product,
    delete_purchase_order,
    delete_quote,
    delete_sales_order,
    update_albaran_status,
    update_client,
    update_product,
    update_purchase_order,
    update_quote,
    update_sales_order,
)
from app.services.sales.queries import (
    get_albaran,
    get_albaran_pdf_data,
    get_quote,
    list_albaranes,
    list_client_invoices,
    list_clients,
    list_products,
    list_purchase_orders,
    list_quotes,
    list_sales_orders,
    list_stock_movements,
)

__all__ = [
    # albaran
    "create_albaran",
    "delete_albaran",
    "get_albaran",
    "get_albaran_pdf_data",
    "list_albaranes",
    "update_albaran_status",
    # client
    "create_client",
    "delete_client",
    "list_client_invoices",
    "list_clients",
    "update_client",
    # product
    "create_product",
    "create_stock_movement",
    "delete_product",
    "list_products",
    "list_stock_movements",
    "update_product",
    # purchase_order
    "create_purchase_order",
    "delete_purchase_order",
    "list_purchase_orders",
    "update_purchase_order",
    # quote
    "convert_to_invoice",
    "create_quote",
    "delete_quote",
    "get_quote",
    "list_quotes",
    "update_quote",
    # sales_order
    "create_sales_order",
    "delete_sales_order",
    "list_sales_orders",
    "update_sales_order",
]
