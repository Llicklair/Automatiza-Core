"""
ERP routes — re-exports sub-routers for backward compatibility.

All endpoints have been split into dedicated modules:
  - clients.py      → /clients
  - products.py     → /products, /products/{id}/stock-movements
  - invoices.py     → /invoices, /clients/{id}/invoices, PDFs
  - sales_orders.py → /orders
  - purchase_orders.py → /purchase-orders
  - recurring_invoices.py → /recurring-invoices
"""

from fastapi import APIRouter

from app.api.v1.routes.clients import router as clients_router
from app.api.v1.routes.invoices import router as invoices_router
from app.api.v1.routes.products import router as products_router
from app.api.v1.routes.purchase_orders import router as purchase_orders_router
from app.api.v1.routes.recurring_invoices import router as recurring_invoices_router
from app.api.v1.routes.sales_orders import router as sales_orders_router

router = APIRouter()

router.include_router(clients_router)
router.include_router(products_router)
router.include_router(invoices_router)
router.include_router(sales_orders_router)
router.include_router(purchase_orders_router)
router.include_router(recurring_invoices_router)
