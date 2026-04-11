from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClientCreate(BaseModel):
    nif: str | None = None
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    client_type: str = "customer"

class ClientResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    nif: str | None = None
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    client_type: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Nuevos Modelos de Facturación Avanzada ---

class ProductCreate(BaseModel):
    item_type: str = "product"  # product | service
    sku: str | None = None
    name: str
    description: str | None = None
    price: float = 0.0
    tax_percentage: float = 21.0
    stock_quantity: int = 0
    stock_min_alert: int = 0

class ProductResponse(ProductCreate):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InvoiceLineCreate(BaseModel):
    product_id: UUID | None = None
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    discount_percentage: float = 0.0
    tax_percentage: float = 21.0
    # No pedimos el 'total' al frontend, lo calcularemos nosotros si queremos mayor seguridad
    # o bien podemos aceptar el total como sugerencia y re-verificarlo.

class InvoiceLineResponse(InvoiceLineCreate):
    id: UUID
    invoice_id: UUID
    total: float

    model_config = ConfigDict(from_attributes=True)

class ClientUpdate(BaseModel):
    nif: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    client_type: str | None = None


class ProductUpdate(BaseModel):
    item_type: str | None = None
    sku: str | None = None
    name: str | None = None
    description: str | None = None
    price: float | None = None
    tax_percentage: float | None = None
    stock_quantity: int | None = None
    stock_min_alert: int | None = None


class InvoiceStatusUpdate(BaseModel):
    status: str


class InvoiceCreate(BaseModel):
    serie: str | None = "F"   # Serie de facturación: F=normal, R=rectificativa, T=simplificada
    invoice_number: str | None = None  # Si se provee se ignora la numeración automática
    date: datetime
    due_date: datetime | None = None
    status: str = "draft"
    invoice_type: str = "issued"
    notes: str | None = None
    terms: str | None = None
    lines: list[InvoiceLineCreate] = []

class InvoiceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    client_id: UUID
    invoice_number: str | None = None
    date: datetime
    due_date: datetime | None = None
    amount_base: float
    tax_amount: float
    amount_total: float
    status: str
    invoice_type: str
    notes: str | None = None
    terms: str | None = None
    external_id: str | None = None
    created_at: datetime
    updated_at: datetime

    client: ClientResponse | None = None
    lines: list[InvoiceLineResponse] = []

    model_config = ConfigDict(from_attributes=True)


# --- Stock / Inventario ---

class StockMovementCreate(BaseModel):
    movement_type: str  # entrada | salida | ajuste
    quantity: int
    reference: str | None = None
    notes: str | None = None

class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    product_id: UUID
    movement_type: str
    quantity: int
    stock_after: int
    reference: str | None = None
    notes: str | None = None
    created_at: datetime


# --- Pedidos de Venta ---

class SalesOrderLineCreate(BaseModel):
    product_id: UUID | None = None
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    discount_percentage: float = 0.0
    tax_percentage: float = 21.0

class SalesOrderLineResponse(SalesOrderLineCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    total: float

class SalesOrderCreate(BaseModel):
    client_id: UUID
    order_number: str | None = None
    date: datetime | None = None
    expected_delivery: datetime | None = None
    notes: str | None = None
    quote_id: UUID | None = None
    lines: list[SalesOrderLineCreate] = []

class SalesOrderUpdate(BaseModel):
    status: str | None = None
    expected_delivery: datetime | None = None
    notes: str | None = None

class SalesOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    client_id: UUID
    order_number: str | None = None
    date: datetime
    expected_delivery: datetime | None = None
    status: str
    amount_base: float
    tax_amount: float
    amount_total: float
    notes: str | None = None
    quote_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    client: ClientResponse | None = None
    lines: list[SalesOrderLineResponse] = []


# --- Pedidos de Compra ---

class PurchaseOrderLineCreate(BaseModel):
    product_id: UUID | None = None
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    tax_percentage: float = 21.0

class PurchaseOrderLineResponse(PurchaseOrderLineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_id: UUID
    total: float

class PurchaseOrderCreate(BaseModel):
    supplier_id: UUID
    order_number: str | None = None
    date: datetime | None = None
    expected_delivery: datetime | None = None
    notes: str | None = None
    lines: list[PurchaseOrderLineCreate] = []

class PurchaseOrderUpdate(BaseModel):
    status: str | None = None
    expected_delivery: datetime | None = None
    notes: str | None = None

class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    supplier_id: UUID
    order_number: str | None = None
    date: datetime
    expected_delivery: datetime | None = None
    status: str
    amount_base: float
    tax_amount: float
    amount_total: float
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    supplier: ClientResponse | None = None
    lines: list[PurchaseOrderLineResponse] = []


# --- Facturación Recurrente ---

from datetime import date as DateType


class RecurringLineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    tax_percentage: float = 21.0

class RecurringInvoiceCreate(BaseModel):
    client_id: UUID
    name: str
    interval_type: str = "monthly"   # monthly | quarterly | yearly | weekly
    next_run_date: DateType
    notes: str | None = None
    terms: str | None = None
    lines: list[RecurringLineItem] = []

class RecurringInvoiceUpdate(BaseModel):
    name: str | None = None
    interval_type: str | None = None
    next_run_date: DateType | None = None
    is_active: bool | None = None
    notes: str | None = None
    terms: str | None = None
    lines: list[RecurringLineItem] | None = None

class RecurringInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    client_id: UUID
    name: str
    interval_type: str
    next_run_date: DateType
    last_run_date: DateType | None = None
    is_active: bool
    lines_json: list[dict]
    notes: str | None = None
    terms: str | None = None
    created_at: datetime
    updated_at: datetime
    client: ClientResponse | None = None
