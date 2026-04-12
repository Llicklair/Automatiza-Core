import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class TransactionReconcile(BaseModel):
    invoice_id: str


class BankTransactionResponse(BaseModel):
    id: uuid.UUID
    date: date
    description: str
    amount: float
    balance: float | None = None
    status: str
    invoice_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)
