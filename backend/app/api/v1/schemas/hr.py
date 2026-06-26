from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EmployeeBase(BaseModel):
    nif: str | None = None
    name: str
    email: str | None = None
    department: str | None = None
    role: str | None = None
    base_salary: float | None = None
    status: str = "active"
    irpf_rate: float | None = None
    num_pagas: int | None = None  # 12 | 14
    prorratear_pagas: bool | None = None
    jornada_tipo: str | None = None  # completa | parcial
    jornada_horas_semana: float | None = None
    join_date: datetime | None = None
    contract_end_date: datetime | None = None
    leave_type: str | None = None
    leave_start: date | None = None
    leave_end: date | None = None


class EmployeeCreate(EmployeeBase):
    jornada_horas_semana: float | None = Field(None, gt=0, le=168)

    @model_validator(mode="after")
    def _check_contract_dates(self):
        if self.join_date and self.contract_end_date and self.contract_end_date < self.join_date:
            raise ValueError("La fecha de fin de contrato no puede ser anterior a la de alta")
        return self


class EmployeeUpdate(BaseModel):
    nif: str | None = None
    name: str | None = None
    email: str | None = None
    department: str | None = None
    role: str | None = None
    base_salary: float | None = None
    status: str | None = None
    irpf_rate: float | None = None
    num_pagas: int | None = None  # 12 | 14
    prorratear_pagas: bool | None = None
    jornada_tipo: str | None = None  # completa | parcial
    jornada_horas_semana: float | None = Field(None, gt=0, le=168)
    join_date: datetime | None = None
    contract_end_date: datetime | None = None
    leave_type: str | None = None
    leave_start: date | None = None
    leave_end: date | None = None

    @model_validator(mode="after")
    def _check_contract_dates(self):
        if self.join_date and self.contract_end_date and self.contract_end_date < self.join_date:
            raise ValueError("La fecha de fin de contrato no puede ser anterior a la de alta")
        return self


class EmployeeResponse(EmployeeBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


# ── Schedules ─────────────────────────────────────────────────────────────────


class ScheduleDay(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str
    active: bool = True


class ScheduleUpsert(BaseModel):
    schedules: list[ScheduleDay]


class ScheduleAISuggestRequest(BaseModel):
    instruction: str
    employee_ids: list[UUID] | None = None


# ── Attendance ────────────────────────────────────────────────────────────────


class ClockInRequest(BaseModel):
    employee_id: UUID
    notes: str | None = None


class AttendanceResponse(BaseModel):
    id: UUID
    employee_id: UUID
    clock_in: datetime
    clock_out: datetime | None = None
    date: date
    notes: str | None = None
    model_config = ConfigDict(from_attributes=True)


# ── Leave Requests ────────────────────────────────────────────────────────────


class ExpenseCreate(BaseModel):
    employee_id: UUID
    amount: float
    category: str
    description: str
    date: date
    notes: str | None = None


class ExpenseUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


class ExpenseResponse(BaseModel):
    id: UUID
    employee_id: UUID
    amount: float
    category: str
    description: str
    date: date
    status: str
    receipt_filename: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    employee: EmployeeResponse | None = None
    model_config = ConfigDict(from_attributes=True)


class LeaveRequestCreate(BaseModel):
    employee_id: UUID
    leave_type: str
    start_date: date
    end_date: date
    notes: str | None = None


class LeaveRequestResponse(BaseModel):
    id: UUID
    employee_id: UUID
    leave_type: str
    start_date: date
    end_date: date
    status: str
    notes: str | None = None
    created_at: datetime
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
    cuota_solidaridad: float = 0.0
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
    horas_extra_importe: float = 0.0
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
    ss_desempleo: float  # 1.55%
    ss_formacion_profesional: float  # 0.10%
    ss_mei: float  # 0.12%
    cuota_solidaridad: float = 0.0  # cotización adicional de solidaridad (> base máx.)
    total_ss: float
    irpf: float
    deductions: float
    net_salary: float
    irpf_rate_applied: float


class PayrollResponse(PayrollBase):
    id: UUID
    tenant_id: UUID
    gross_salary: float | None = None
    devengos_json: dict | None = None
    created_at: datetime
    employee: EmployeeResponse | None = None
    model_config = ConfigDict(from_attributes=True)


# ── Schemas para generación de PDFs HR ──────────────────────────────────────


class FiniquitoConcepto(BaseModel):
    concepto: str
    importe: float


class FiniquitoRequest(BaseModel):
    employee_id: UUID
    fecha_baja: str
    causa_baja: str = "Baja voluntaria"
    # Con conceptos vacios el backend calcula el finiquito automaticamente
    vacaciones_pendientes_dias: float = 0.0
    conceptos: list[FiniquitoConcepto] = []
    total_percepciones: float = 0.0
    total_deducciones: float = 0.0
    liquido: float = 0.0


class LiquidacionConcepto(BaseModel):
    concepto: str
    unidad: str = ""
    devengos: float = 0.0
    deducciones: float = 0.0


class LiquidacionRequest(BaseModel):
    employee_id: UUID
    fecha_baja: str
    causa_baja: str = "Baja voluntaria"
    conceptos: list[LiquidacionConcepto] = []
    total_devengos: float = 0.0
    total_deducciones: float = 0.0
    liquido: float = 0.0


class RegistroJornadaDia(BaseModel):
    dia: int
    entrada: str = ""
    salida: str = ""
    horas_ordinarias: float = 0.0
    incidencias: str = ""
    horas_extras: float = 0.0


class RegistroJornadaRequest(BaseModel):
    employee_id: UUID
    mes: int
    anio: int
    registros: list[RegistroJornadaDia] = []
    total_horas_ordinarias: float = 0.0
    total_horas_extras: float = 0.0
