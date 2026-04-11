"""Modelos RRHH: Empleados, Nóminas, Finiquitos y Reclutamiento."""

from .common import (
    JSONB,
    UUID,
    Base,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    relationship,
    utcnow,
    uuid,
)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Identificación
    nif = Column(String(20), index=True)  # DNI/NIE
    numero_afiliacion_ss = Column(String(20))  # NAF — Número de Afiliación SS
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    birth_date = Column(DateTime(timezone=True))

    # Datos laborales
    department = Column(String(100))
    role = Column(String(100))
    categoria_profesional = Column(String(100))  # dentro del convenio
    grupo_cotizacion = Column(String(2))  # '01'–'11' (RGSS)
    tipo_contrato = Column(
        String(10)
    )  # código SEPE: 100=indefinido, 150=indef. parcial, 401=obra/servicio…
    convenio_colectivo = Column(String(255))

    # Jornada
    jornada_tipo = Column(String(20), default="completa")  # completa | parcial
    jornada_horas_semana = Column(Numeric(4, 1))  # e.g. 40.0

    # Bonificación SEPE aplicable al contrato
    # conversion_temporal | discapacidad | exclusion_social | mayor_45 | hogar_familiar | otras
    bonificacion_tipo = Column(String(50))

    # Retribución e IRPF
    base_salary = Column(Numeric(10, 2))
    irpf_rate = Column(Numeric(5, 2), default=15.00)

    # Fechas contractuales
    join_date = Column(DateTime(timezone=True))
    contract_end_date = Column(DateTime(timezone=True))
    periodo_prueba_dias = Column(Integer)

    status = Column(String(50), default="active")  # active | inactive | leave

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    payrolls = relationship("Payroll", back_populates="employee", lazy="dynamic")
    settlements = relationship("Settlement", back_populates="employee", lazy="dynamic")


class Payroll(Base):
    __tablename__ = "payrolls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True)

    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    issue_date = Column(DateTime(timezone=True), nullable=False)

    # ── Devengos ──────────────────────────────────────────────────────────────
    base_salary = Column(Numeric(10, 2), nullable=False)  # salario base del período
    gross_salary = Column(Numeric(10, 2))  # total devengos (bruto)
    devengos_json = Column(JSONB)  # {"plus_convenio": x, "horas_extra": x, "prorrata_extra": x, …}

    # ── Bases de cotización ───────────────────────────────────────────────────
    base_cotizacion_cc = Column(Numeric(10, 2))  # base contingencias comunes
    base_irpf = Column(Numeric(10, 2))  # base sujeta a retención IRPF

    # ── Porcentajes SS trabajador (legales 2024) ──────────────────────────────
    pct_cc = Column(Numeric(5, 2), default=4.70)  # contingencias comunes trabajador
    pct_desempleo = Column(Numeric(5, 2), default=1.55)  # desempleo trabajador (tipo general)
    pct_fp = Column(Numeric(5, 2), default=0.10)  # formación profesional
    pct_mei = Column(Numeric(5, 2), default=0.10)  # MEI trabajador

    # ── Deducciones (importes) ────────────────────────────────────────────────
    ss_contingencias_comunes = Column(Numeric(10, 2), default=0)
    ss_desempleo = Column(Numeric(10, 2), default=0)
    ss_formacion_profesional = Column(Numeric(10, 2), default=0)
    ss_mei = Column(Numeric(10, 2), default=0)
    irpf = Column(Numeric(10, 2), default=0)
    pct_irpf = Column(Numeric(5, 2), default=15.00)  # % IRPF aplicado
    anticipos = Column(Numeric(10, 2), default=0)
    other_deductions = Column(Numeric(10, 2), default=0)
    deductions = Column(Numeric(10, 2), default=0)  # total deducciones

    # ── Cuotas empresa (informativo en nómina) ────────────────────────────────
    # {"cc": x, "at_ep": x, "desempleo": x, "fogasa": x, "fp": x, "mei": x}
    cuotas_empresa_json = Column(JSONB)

    net_salary = Column(Numeric(10, 2), nullable=False)  # líquido a percibir
    status = Column(String(50), default="draft")  # draft | approved | paid

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    employee = relationship("Employee", back_populates="payrolls")


class Settlement(Base):
    """Finiquito — liquidación al término de la relación laboral."""

    __tablename__ = "settlements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True)

    fecha_extincion = Column(DateTime(timezone=True), nullable=False)
    # baja_voluntaria | despido_objetivo | despido_improcedente | fin_contrato | mutuo_acuerdo | jubilacion
    causa_extincion = Column(String(50), nullable=False)

    # ── Percepciones ─────────────────────────────────────────────────────────
    vacaciones_pendientes_dias = Column(Numeric(5, 1), default=0)
    vacaciones_pendientes_importe = Column(Numeric(10, 2), default=0)
    prorrata_paga_extra = Column(Numeric(10, 2), default=0)
    prorrata_aguinaldo = Column(Numeric(10, 2), default=0)
    indemnizacion = Column(Numeric(10, 2), default=0)  # 20 días/año (objetivo) o 33 (improcedente)
    otros_conceptos_json = Column(JSONB)  # conceptos adicionales libres
    total_percepciones = Column(Numeric(10, 2), nullable=False)

    # ── Deducciones ───────────────────────────────────────────────────────────
    deduccion_ss = Column(Numeric(10, 2), default=0)
    deduccion_irpf = Column(Numeric(10, 2), default=0)
    total_deducciones = Column(Numeric(10, 2), default=0)

    total_liquido = Column(Numeric(10, 2), nullable=False)

    pdf_path = Column(String(500))
    signed_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    status = Column(String(20), default="draft")  # draft | signed | archived

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    employee = relationship("Employee", back_populates="settlements")


# ── Registro de jornada (Art. 34.9 ET — obligatorio desde 2019) ───────────────


class JornadaRecord(Base):
    """Registro diario de jornada por empleado.

    Obligatorio legalmente (Real Decreto-ley 8/2019). El listado mensual
    debe ser firmado por empresa y trabajador y conservarse 4 años.
    """

    __tablename__ = "jornada_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True)

    fecha = Column(Date, nullable=False)  # día concreto
    hora_entrada = Column(String(5))  # "07:00"
    hora_salida = Column(String(5))  # "15:00"
    horas_ordinarias = Column(Numeric(4, 2), default=0)  # horas computadas como ordinarias
    horas_extra = Column(Numeric(4, 2), default=0)  # horas extraordinarias
    horas_extra_voluntarias = Column(Numeric(4, 2), default=0)  # horas extra voluntarias
    notas = Column(String(255))  # ausencias, permisos, IT, etc.

    # Mes al que pertenece este registro (para agrupar el listado mensual)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = relationship("Tenant")
    employee = relationship("Employee")


# ── Reclutamiento ─────────────────────────────────────────────────────────────


class RecruitmentPosition(Base):
    """Puesto abierto para cubrir."""

    __tablename__ = "recruitment_positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    department = Column(String(100))
    description = Column(Text)
    required_skills = Column(JSONB, default=list)  # ["Python", "SQL", ...]
    experience_min_years = Column(Numeric(4, 1), default=0)
    salary_range_min = Column(Numeric(10, 2))
    salary_range_max = Column(Numeric(10, 2))
    status = Column(String(50), default="open")  # open | closed | paused
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    candidates = relationship("Candidate", back_populates="position")


class Candidate(Base):
    """Candidato vinculado a un puesto."""

    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    position_id = Column(UUID(as_uuid=True), ForeignKey("recruitment_positions.id"), index=True)

    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))

    # Datos extraídos del CV por IA
    skills = Column(JSONB, default=list)  # ["React", "Node.js", ...]
    experience_years = Column(Numeric(4, 1))
    languages = Column(JSONB, default=list)  # [{"lang": "Español", "level": "nativo"}, ...]
    education = Column(Text)
    summary = Column(Text)  # Resumen generado por IA
    raw_cv_text = Column(Text)  # Texto completo extraído

    cv_file_path = Column(String(500))  # Ruta al PDF original
    score = Column(Numeric(5, 2))  # 0-100 fit score
    score_breakdown = Column(JSONB)  # {"skills": 80, "experience": 60, ...}

    status = Column(String(50), default="new")  # new | reviewed | shortlisted | rejected | hired
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    position = relationship("RecruitmentPosition", back_populates="candidates")
