"""Modelos RRHH: Empleados, Nóminas y Reclutamiento."""

from .common import (
    Base, Column, DateTime, ForeignKey, Numeric, String, Text, UUID, JSONB,
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


# ── Reclutamiento ─────────────────────────────────────────────────────────────

class RecruitmentPosition(Base):
    """Puesto abierto para cubrir."""
    __tablename__ = 'recruitment_positions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    department = Column(String(100))
    description = Column(Text)
    required_skills = Column(JSONB, default=list)      # ["Python", "SQL", ...]
    experience_min_years = Column(Numeric(4, 1), default=0)
    salary_range_min = Column(Numeric(10, 2))
    salary_range_max = Column(Numeric(10, 2))
    status = Column(String(50), default='open')        # open | closed | paused
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship('Tenant')
    candidates = relationship('Candidate', back_populates='position')


class Candidate(Base):
    """Candidato vinculado a un puesto."""
    __tablename__ = 'candidates'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    position_id = Column(UUID(as_uuid=True), ForeignKey('recruitment_positions.id'), index=True)

    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))

    # Datos extraídos del CV por IA
    skills = Column(JSONB, default=list)               # ["React", "Node.js", ...]
    experience_years = Column(Numeric(4, 1))
    languages = Column(JSONB, default=list)             # [{"lang": "Español", "level": "nativo"}, ...]
    education = Column(Text)
    summary = Column(Text)                             # Resumen generado por IA
    raw_cv_text = Column(Text)                         # Texto completo extraído

    cv_file_path = Column(String(500))                 # Ruta al PDF original
    score = Column(Numeric(5, 2))                      # 0-100 fit score
    score_breakdown = Column(JSONB)                    # {"skills": 80, "experience": 60, ...}

    status = Column(String(50), default='new')         # new | reviewed | shortlisted | rejected | hired
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship('Tenant')
    position = relationship('RecruitmentPosition', back_populates='candidates')
