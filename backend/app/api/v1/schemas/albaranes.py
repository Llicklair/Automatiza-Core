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
    model_config = {"from_attributes": True}
