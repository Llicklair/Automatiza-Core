"""Pydantic schemas for the Scanner module."""

from datetime import date

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
    # Lote OPCIONAL (gestión FEFO). En `entrada`, si se indica `lot_number`,
    # se registra el lote con su caducidad. En `salida` se ignoran: el descuento
    # FEFO es automático sobre los lotes existentes. Todo retrocompatible.
    lot_number: str | None = None
    expiry_date: date | None = None
    cost_price: float | None = None


class ConfirmDeliveryRequest(BaseModel):
    albaran_number: str
