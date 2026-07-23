"""Pydantic schemas for albaranes (delivery notes)."""

from datetime import date as date_type
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DeliveryNoteLineCreate(BaseModel):
    product_id: UUID | None = None
    description: str
    quantity: float = 1
    unit_price: float = 0
    tax_percentage: float = 21


class DeliveryNoteCreate(BaseModel):
    client_id: UUID | None = None
    client_name: str | None = None
    date: date_type | None = None
    notes: str | None = None
    lines: list[DeliveryNoteLineCreate] = []


class DeliveryNoteUpdate(BaseModel):
    """Edición T8. None = no tocar; "" en notes/client_name = limpiar."""

    client_id: UUID | None = None
    client_name: str | None = None
    date: date_type | None = None
    notes: str | None = None
    lines: list[DeliveryNoteLineCreate] | None = None


class DeliveryNoteStatusUpdate(BaseModel):
    status: str  # draft, confirmed, delivered


class DeliveryNoteLineResponse(BaseModel):
    id: UUID
    product_id: UUID | None = None
    description: str
    quantity: float
    unit_price: float
    tax_percentage: float
    total: float
    model_config = {"from_attributes": True}


class DeliveryNoteResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    client_id: UUID | None = None
    albaran_number: str
    date: date_type
    status: str
    notes: str | None = None
    amount_base: float
    tax_amount: float
    amount_total: float
    created_at: datetime | None = None
    lines: list[DeliveryNoteLineResponse] = []
    # T7: facturas enlazadas (lo puebla list_albaranes; vacío en otras rutas).
    invoice_ids: list[UUID] = []
    # Datos del cliente (solo en el listado): buscador por nombre/NIF/tel/email.
    client_name: str | None = None
    client_nif: str | None = None
    client_phone: str | None = None
    client_email: str | None = None
    model_config = {"from_attributes": True}


class FacturarAlbaranesRequest(BaseModel):
    albaran_ids: list[UUID]
