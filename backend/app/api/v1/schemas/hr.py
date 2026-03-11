from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EmployeeBase(BaseModel):
    nif: str | None = None
    name: str
    department: str | None = None
    role: str | None = None
    base_salary: float | None = None
    status: str = "active"
    join_date: datetime | None = None
    contract_end_date: datetime | None = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    nif: str | None = None
    name: str | None = None
    department: str | None = None
    role: str | None = None
    base_salary: float | None = None
    status: str | None = None
    join_date: datetime | None = None
    contract_end_date: datetime | None = None

class EmployeeResponse(EmployeeBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

class PayrollBase(BaseModel):
    employee_id: UUID
    period_start: datetime
    period_end: datetime
    issue_date: datetime
    base_salary: float
    deductions: float = 0.0
    net_salary: float
    status: str = "draft"

class PayrollCreate(PayrollBase):
    pass

class PayrollResponse(PayrollBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    employee: EmployeeResponse | None = None
    model_config = ConfigDict(from_attributes=True)
