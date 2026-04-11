"""Modelos contables: Asientos, Transacciones bancarias e Inmovilizado."""

from .common import (
    UUID,
    Base,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    relationship,
    utcnow,
    uuid,
)


class JournalEntry(Base):
    __tablename__ = 'journal_entries'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)

    date = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    description = Column(String(500), nullable=False)
    reference_id = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = relationship('Tenant')
    lines = relationship('JournalLine', back_populates='entry', cascade='all, delete-orphan')


class JournalLine(Base):
    __tablename__ = 'journal_lines'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    entry_id = Column(UUID(as_uuid=True), ForeignKey('journal_entries.id'), nullable=False, index=True)

    account_code = Column(String(50), nullable=False, index=True)
    account_name = Column(String(255), nullable=True)

    debit = Column(Numeric(15, 2), default=0)
    credit = Column(Numeric(15, 2), default=0)

    entry = relationship('JournalEntry', back_populates='lines')
    tenant = relationship('Tenant')


class BankTransaction(Base):
    __tablename__ = 'bank_transactions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)

    date = Column(Date, nullable=False)
    description = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    balance = Column(Numeric(10, 2))
    status = Column(String(50), default='unreconciled')
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoices.id'), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = relationship('Tenant')
    invoice = relationship('Invoice')


class FixedAsset(Base):
    __tablename__ = 'fixed_assets'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    purchase_date = Column(Date, nullable=False)
    purchase_value = Column(Numeric(15, 2), nullable=False)
    useful_life_years = Column(Numeric(5, 2), nullable=False, default=5)
    residual_value = Column(Numeric(15, 2), nullable=False, default=0)
    depreciation_method = Column(String(50), nullable=False, default='linear')
    status = Column(String(50), nullable=False, default='active')
    account_code = Column(String(50), nullable=True, default='213')
    reference_invoice = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = relationship('Tenant')
