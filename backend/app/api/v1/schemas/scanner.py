"""Pydantic schemas for the Scanner module."""

from pydantic import BaseModel


class GenerateQRRequest(BaseModel):
    device_name: str = "Scanner móvil"


class ScanProductRequest(BaseModel):
    # Acepta SKU o código de barras. El campo conserva el nombre `sku` por
    # compatibilidad con clientes antiguos; el servicio busca por barcode
    # primero y por SKU como fallback.
    sku: str


class StockMovementRequest(BaseModel):
    # `sku` acepta SKU o código de barras (ver ScanProductRequest).
    sku: str
    quantity: float
    notes: str = ""


class ConfirmDeliveryRequest(BaseModel):
    albaran_number: str
