"""Modelos RRHH: Empleados y Nominas."""

from .common import (
    Base, Column, DateTime, ForeignKey, Numeric, String, UUID,
    relationship, uuid, utcnow,
)


class Employee(Base):
    __tablename__ = 'employees'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    nif = Column(String(50), index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    department = Column(String(100))
    role = Column(String(100))
    base_salary = Column(Numeric(10, 2))
    status = Column(String(50), default='active')
    irpf_rate = Column(Numeric(5, 2), default=15.00)

    join_date = Column(DateTime(timezone=True))
    contract_end_date = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship('Tenant')


class Payroll(Base):
    __tablename__ = 'payrolls'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey('employees.id'), nullable=False, index=True)

    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    issue_date = Column(DateTime(timezone=True), nullable=False)

    base_salary = Column(Numeric(10, 2), nullable=False)
    ss_contingencias_comunes = Column(Numeric(10, 2), default=0)
    ss_desempleo = Column(Numeric(10, 2), default=0)
    ss_formacion_profesional = Column(Numeric(10, 2), default=0)
    ss_mei = Column(Numeric(10, 2), default=0)
    irpf = Column(Numeric(10, 2), default=0)
    other_deductions = Column(Numeric(10, 2), default=0)
    deductions = Column(Numeric(10, 2), default=0)
    net_salary = Column(Numeric(10, 2), nullable=False)

    status = Column(String(50), default='draft')

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship('Tenant')
    employee = relationship('Employee')
