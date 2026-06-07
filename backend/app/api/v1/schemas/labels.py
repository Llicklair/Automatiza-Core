"""Schemas de impresión de etiquetas."""

from uuid import UUID

from pydantic import BaseModel


class LabelItem(BaseModel):
    product_id: UUID
    copies: int = 1


class LabelsRequest(BaseModel):
    items: list[LabelItem]
    show_price: bool = True
