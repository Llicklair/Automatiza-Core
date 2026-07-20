"""Schemas Pydantic para TPV (Punto de Venta)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PosLineAdd(BaseModel):
    """Añadir línea al carrito. Si `product_id` viene, se completa
    description/unit_price/tax_percentage desde el producto al servidor."""

    product_id: UUID | None = None
    description: str | None = None
    quantity: int = Field(default=1, gt=0)
    unit_price: float | None = None
    tax_percentage: float | None = None


class PosLineUpdate(BaseModel):
    quantity: int = Field(gt=0)


class PosLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    product_id: UUID | None = None
    description: str
    quantity: int
    unit_price: float
    tax_percentage: float
    total: float
    created_at: datetime


class PosSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    user_id: UUID
    status: str
    payment_method: str | None = None
    amount_subtotal: float
    tax_amount: float
    amount_total: float
    notes: str | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    lines: list[PosLineResponse] = []


class PosCheckoutRequest(BaseModel):
    payment_method: Literal["cash", "card"]
    notes: str | None = None


class VerifactuQr(BaseModel):
    huella: str
    verify_url: str


class PosFacturaResponse(BaseModel):
    """Factura simplificada (F2) emitida desde el TPV, con su QR Verifactu.

    `verifactu` es None cuando el tenant no está en modo Verifactu (no hay registro
    encadenado) → el ticket sale sin QR, igual que el PDF.
    """

    id: UUID
    invoice_number: str | None = None
    invoice_type: str
    status: str
    amount_total: float
    is_simplified: bool
    verifactu: VerifactuQr | None = None
