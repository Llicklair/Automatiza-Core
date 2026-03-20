from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EmployeeBase(BaseModel):
    nif: str | None = None
    name: str
    email: str | None = None
    department: str | None = None
    role: str | None = None
    base_salary: float | None = None
    status: str = "active"
    irpf_rate: float | None = None
    join_date: datetime | None = None
    contract_end_date: datetime | None = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    nif: str | None = None
    name: str | None = None
    email: str | None = None
    department: str | None = None
    role: str | None = None
    base_salary: float | None = None
    status: str | None = None
    irpf_rate: float | None = None
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
    ss_contingencias_comunes: float = 0.0
    ss_desempleo: float = 0.0
    ss_formacion_profesional: float = 0.0
    ss_mei: float = 0.0
    irpf: float = 0.0
    other_deductions: float = 0.0
    deductions: float = 0.0
    net_salary: float
    status: str = "draft"

class PayrollCreate(PayrollBase):
    pass


class PayrollSimpleCreate(BaseModel):
    """Crea nómina con cálculo automático de SS e IRPF (tasas reales 2025)."""
    employee_id: UUID
    period_start: datetime
    period_end: datetime
    issue_date: datetime | None = None
    base_salary: float | None = None  # Si None, usa employee.base_salary
    status: str = "draft"


class PayrollUpdate(BaseModel):
    period_start: datetime | None = None
    period_end: datetime | None = None
    issue_date: datetime | None = None
    base_salary: float | None = None
    other_deductions: float | None = None
    status: str | None = None


class PayrollCalculateResponse(BaseModel):
    """Previsualización del cálculo de nómina sin crear el registro."""
    employee_id: UUID
    base_salary: float
    ss_contingencias_comunes: float  # 4.70%
    ss_desempleo: float              # 1.55%
    ss_formacion_profesional: float  # 0.10%
    ss_mei: float                    # 0.12%
    total_ss: float
    irpf: float
    deductions: float
    net_salary: float
    irpf_rate_applied: float

class PayrollResponse(PayrollBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    employee: EmployeeResponse | None = None
    model_config = ConfigDict(from_attributes=True)
