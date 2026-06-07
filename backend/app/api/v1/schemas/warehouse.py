"""Schemas de almacenes (multi-almacén)."""

from uuid import UUID

from pydantic import BaseModel


class WarehouseCreate(BaseModel):
    name: str
    code: str | None = None
    address: str | None = None
    is_default: bool = False
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class StockTransferRequest(BaseModel):
    """Transferencia de stock de un almacén a otro."""

    product_id: UUID
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    quantity: int
