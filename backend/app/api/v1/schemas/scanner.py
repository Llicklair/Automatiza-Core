"""Pydantic schemas for the Scanner module."""

from pydantic import BaseModel


class GenerateQRRequest(BaseModel):
    device_name: str = "Scanner móvil"


class ScanProductRequest(BaseModel):
    sku: str


class StockMovementRequest(BaseModel):
    sku: str
    quantity: float
    notes: str = ""


class ConfirmDeliveryRequest(BaseModel):
    albaran_number: str
