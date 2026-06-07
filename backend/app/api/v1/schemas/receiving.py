"""Schemas de recepción de mercancía contra pedido de compra."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class ReceiveLine(BaseModel):
    line_id: UUID
    quantity: float
    lot_number: str | None = None
    expiry_date: date | None = None


class ReceiveRequest(BaseModel):
    warehouse_id: UUID | None = None
    lines: list[ReceiveLine]
