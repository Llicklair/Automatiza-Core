"""Sales domain services."""

from app.services.sales.albaran import (
    create_albaran,
    delete_albaran,
    get_albaran,
    get_albaran_pdf_data,
    list_albaranes,
    update_albaran_status,
)
from app.services.sales.client import (
    create_client,
    delete_client,
    list_client_invoices,
    list_clients,
    update_client,
)
from app.services.sales.product import (
    create_product,
    create_stock_movement,
    delete_product,
    list_products,
    list_stock_movements,
    update_product,
)
from app.services.sales.purchase_order import (
    create_purchase_order,
    delete_purchase_order,
    list_purchase_orders,
    update_purchase_order,
)
from app.services.sales.quote import (
    convert_to_invoice,
    create_quote,
    delete_quote,
    get_quote,
    list_quotes,
    update_quote,
)
from app.services.sales.sales_order import (
    create_sales_order,
    delete_sales_order,
    list_sales_orders,
    update_sales_order,
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
