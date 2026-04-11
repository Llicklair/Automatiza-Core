from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class QuoteLineBase(BaseModel):
    product_id: UUID | None = None
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    tax_percentage: float = 21.0


class QuoteLineCreate(QuoteLineBase):
    pass


class QuoteLineResponse(QuoteLineBase):
    id: UUID
    quote_id: UUID
    total_line: float
    model_config = ConfigDict(from_attributes=True)


class QuoteBase(BaseModel):
    client_id: UUID
    quote_number: str | None = None
    date: datetime | None = None
    valid_until: datetime | None = None
    amount_base: float = 0.0
    tax_amount: float = 0.0
    amount_total: float = 0.0
    status: str = "draft"
    notes: str | None = None
    terms: str | None = None
    opportunity_id: UUID | None = None


class QuoteCreate(QuoteBase):
    lines: list[QuoteLineCreate] = []


class QuoteUpdate(BaseModel):
    client_id: UUID | None = None
    status: str | None = None
    valid_until: datetime | None = None
    notes: str | None = None
    terms: str | None = None


class QuoteResponse(QuoteBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    lines: list[QuoteLineResponse] = []

    # Client summary to avoid fetching big objects on simple grids
    class ClientBrief(BaseModel):
        id: UUID
        name: str
        nif: str | None = None
        model_config = ConfigDict(from_attributes=True)

    client: ClientBrief | None = None

    model_config = ConfigDict(from_attributes=True)
