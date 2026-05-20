"""Modelos contables: Asientos, Transacciones bancarias e Inmovilizado."""

from sqlalchemy import LargeBinary

from .common import (
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


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    date = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    description = Column(String(500), nullable=False)
    reference_id = Column(String(255), nullable=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True, index=True)
    payroll_id = Column(UUID(as_uuid=True), ForeignKey("payrolls.id"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = relationship("Tenant")
    invoice = relationship("Invoice", foreign_keys=[invoice_id])
    payroll = relationship("Payroll", foreign_keys=[payroll_id])
    lines = relationship("JournalLine", back_populates="entry", cascade="all, delete-orphan")


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    entry_id = Column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False, index=True
    )

    account_code = Column(String(50), nullable=False, index=True)
    account_name = Column(String(255), nullable=True)

    debit = Column(Numeric(15, 2), default=0)
    credit = Column(Numeric(15, 2), default=0)

    entry = relationship("JournalEntry", back_populates="lines")
    tenant = relationship("Tenant")


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    date = Column(Date, nullable=False)
    description = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    balance = Column(Numeric(10, 2))
    status = Column(String(50), default="unreconciled")
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = relationship("Tenant")
    invoice = relationship("Invoice")
    journal_entry = relationship("JournalEntry", foreign_keys=[journal_entry_id])


class FixedAsset(Base):
    __tablename__ = "fixed_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    purchase_date = Column(Date, nullable=False)
    purchase_value = Column(Numeric(15, 2), nullable=False)
    useful_life_years = Column(Numeric(5, 2), nullable=False, default=5)
    residual_value = Column(Numeric(15, 2), nullable=False, default=0)
    depreciation_method = Column(String(50), nullable=False, default="linear")
    status = Column(String(50), nullable=False, default="active")
    account_code = Column(String(50), nullable=True, default="213")
    reference_invoice = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = relationship("Tenant")


class AccountingPeriod(Base):
    """Cierre contable de un periodo (mes, trimestre o ejercicio).

    Cuando un periodo está cerrado (`status='closed'`), no se permiten
    nuevos asientos, edición ni borrado de los existentes dentro del rango
    de fechas del periodo. Reabrir requiere motivo y queda auditado.
    """

    __tablename__ = "accounting_periods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    year = Column(Integer, nullable=False)
    kind = Column(String(16), nullable=False)            # 'month' | 'quarter' | 'year'
    period_index = Column(Integer, nullable=False)       # 1..12 mes, 1..4 trimestre, 0 año

    status = Column(String(16), nullable=False, default="closed")  # 'closed' | 'reopened'
    closed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    closed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reopened_at = Column(DateTime(timezone=True), nullable=True)
    reopened_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reopen_reason = Column(String(500), nullable=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = relationship("Tenant")


class TenantCertificate(Base):
    """Certificado digital del tenant para firma de presentaciones AEAT.

    El contenido .pfx y la contraseña se guardan cifrados con la clave Fernet
    global (`TENANT_ENCRYPTION_KEY`). Solo se descifran en memoria al firmar.
    """

    __tablename__ = "tenant_certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    label = Column(String(120), nullable=False)
    subject_cn = Column(String(255), nullable=True)
    issuer_cn = Column(String(255), nullable=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    serial_number = Column(String(80), nullable=True)
    sha256_fingerprint = Column(String(80), nullable=True)
    encrypted_pfx = Column(LargeBinary, nullable=False)
    encrypted_password = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="active")
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(String(500), nullable=True)

    tenant = relationship("Tenant")


class AeatPresentation(Base):
    """Registro auditado de cada intento de presentación electrónica a la SEDE AEAT."""

    __tablename__ = "aeat_presentations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    model_code = Column(String(10), nullable=False)
    year = Column(Integer, nullable=False)
    period = Column(String(10), nullable=False)
    environment = Column(String(20), nullable=False, default="preproduccion")
    status = Column(String(30), nullable=False, default="pending")

    xml_unsigned = Column(Text, nullable=True)
    xml_signed = Column(Text, nullable=True)
    response_raw = Column(Text, nullable=True)
    csv_justificante = Column(String(80), nullable=True)
    error_code = Column(String(40), nullable=True)
    error_message = Column(Text, nullable=True)

    submitted_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    tenant = relationship("Tenant")
