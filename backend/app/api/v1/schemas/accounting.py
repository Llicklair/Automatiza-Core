from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


# --- Journal Lines ---
class JournalLineBase(BaseModel):
    account_code: str
    account_name: str | None = None
    debit: float = 0.0
    credit: float = 0.0


class JournalLineCreate(JournalLineBase):
    @model_validator(mode="after")
    def _check_line(self):
        if self.debit < 0 or self.credit < 0:
            raise ValueError("El debe y el haber no pueden ser negativos")
        if self.debit > 0 and self.credit > 0:
            raise ValueError("Una línea no puede tener debe y haber a la vez")
        if self.debit == 0 and self.credit == 0:
            raise ValueError("Cada línea debe tener importe en el debe o en el haber")
        return self


class JournalLineResponse(JournalLineBase):
    id: UUID
    tenant_id: UUID
    entry_id: UUID
    model_config = ConfigDict(from_attributes=True)


# --- Journal Entries ---
class JournalEntryBase(BaseModel):
    date: datetime
    description: str
    reference_id: str | None = None


class JournalEntryCreate(JournalEntryBase):
    lines: list[JournalLineCreate]


class JournalEntryResponse(JournalEntryBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    lines: list[JournalLineResponse] = []
    model_config = ConfigDict(from_attributes=True)


# --- Fixed Assets ---
class FixedAssetBase(BaseModel):
    name: str
    category: str | None = None
    description: str | None = None
    purchase_date: date
    purchase_value: float
    useful_life_years: float = 5.0
    residual_value: float = 0.0
    depreciation_method: str = "linear"
    status: str = "active"
    account_code: str | None = "213"
    reference_invoice: str | None = None
    notes: str | None = None


class FixedAssetCreate(FixedAssetBase):
    pass


class FixedAssetUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    purchase_date: date | None = None
    purchase_value: float | None = None
    useful_life_years: float | None = None
    residual_value: float | None = None
    depreciation_method: str | None = None
    status: str | None = None
    account_code: str | None = None
    reference_invoice: str | None = None
    notes: str | None = None


class FixedAssetResponse(FixedAssetBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
