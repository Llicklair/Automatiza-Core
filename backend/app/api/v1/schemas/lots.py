"""Schemas para la gestión de lotes de producto."""

from datetime import date

from pydantic import BaseModel


class LotUpdate(BaseModel):
    """Edición de metadatos de un lote. La cantidad NO se edita aquí (cambia solo
    vía movimientos de stock). Solo se aplican los campos enviados."""

    lot_number: str | None = None
    expiry_date: date | None = None
    cost_price: float | None = None
