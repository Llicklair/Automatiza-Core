from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ─── Client Schemas ─────────────────────────────────────────────────────────

class ClientBase(BaseModel):
    nif: str | None = None
    name: str = Field(..., max_length=255)
    email: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    client_type: str = "customer"

class ClientCreate(ClientBase):
    pass

class ClientOut(ClientBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ─── Invoice Schemas ────────────────────────────────────────────────────────

class InvoiceBase(BaseModel):
    client_id: UUID
    invoice_number: str | None = None
    date: datetime
    amount_base: float = 0.0
    tax_percentage: float = 21.0
    tax_amount: float = 0.0
    amount_total: float = 0.0
    status: str = "draft"
    invoice_type: str = "issued"
    external_id: str | None = None

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceOut(InvoiceBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    client: ClientOut | None = None

    model_config = ConfigDict(from_attributes=True)


# ─── Employee Schemas ───────────────────────────────────────────────────────

class EmployeeBase(BaseModel):
    nif: str | None = None
    name: str = Field(..., max_length=255)
    department: str | None = None
    role: str | None = None
    base_salary: float | None = None
    status: str = "active"
    join_date: datetime | None = None
    contract_end_date: datetime | None = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeOut(EmployeeBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
