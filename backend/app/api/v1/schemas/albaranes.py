"""Pydantic schemas for albaranes (delivery notes)."""

from datetime import date as date_type
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class DeliveryNoteLineCreate(BaseModel):
    product_id: Optional[UUID] = None
    description: str
    quantity: float = 1
    unit_price: float = 0
    tax_percentage: float = 21


class DeliveryNoteCreate(BaseModel):
    client_id: Optional[UUID] = None
    client_name: Optional[str] = None
    date: Optional[date_type] = None
    notes: Optional[str] = None
    lines: List[DeliveryNoteLineCreate] = []


class DeliveryNoteStatusUpdate(BaseModel):
    status: str  # draft, confirmed, delivered


class DeliveryNoteLineResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    description: str
    quantity: float
    unit_price: float
    tax_percentage: float
    total: float
    model_config = {"from_attributes": True}


class DeliveryNoteResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    client_id: Optional[UUID] = None
    albaran_number: str
    date: date_type
    status: str
    notes: Optional[str] = None
    amount_base: float
    tax_amount: float
    amount_total: float
    created_at: Optional[datetime] = None
    lines: List[DeliveryNoteLineResponse] = []
    model_config = {"from_attributes": True}
