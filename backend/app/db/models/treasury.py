"""Modelos de tesorería — remesas SEPA persistidas (pain.001 / pain.008).

Ciclo de vida de una remesa:
    draft → generated → sent → executed → reconciled
(`draft` solo si se guarda sin XML; lo normal es nacer `generated`).
"""

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.models.common import utcnow


class SepaRemittance(Base):
    """Remesa SEPA generada: transferencias (pain.001) o adeudos (pain.008)."""

    __tablename__ = "sepa_remittances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    remittance_type = Column(String(20), nullable=False)  # pain.001 | pain.008
    msg_id = Column(String(35), nullable=False, index=True)
    status = Column(String(20), default="generated", nullable=False)
    # generated | sent | executed | reconciled

    execution_date = Column(Date, nullable=False)
    party_iban = Column(String(34), nullable=False)  # ordenante (001) / acreedor (008)
    nb_of_txs = Column(Integer, nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    xml = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=False)

    executed_at = Column(DateTime(timezone=True), nullable=True)
    bank_transaction_id = Column(
        UUID(as_uuid=True), ForeignKey("bank_transactions.id"), nullable=True
    )

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    orders = relationship(
        "SepaRemittanceOrder",
        back_populates="remittance",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SepaRemittanceOrder(Base):
    """Orden individual dentro de una remesa (transferencia o adeudo)."""

    __tablename__ = "sepa_remittance_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    remittance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sepa_remittances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    counterparty_name = Column(String(140), nullable=False)
    counterparty_iban = Column(String(34), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    concept = Column(String(140), default="")
    end_to_end_id = Column(String(35), nullable=False)

    # Solo adeudos (pain.008): datos del mandato SEPA Core
    mandate_id = Column(String(35), nullable=True)
    mandate_date = Column(Date, nullable=True)
    sequence_type = Column(String(4), nullable=True)  # FRST | RCUR | OOFF | FNAL

    # Trazabilidad opcional con el origen
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    payroll_id = Column(UUID(as_uuid=True), ForeignKey("payrolls.id"), nullable=True)

    remittance = relationship("SepaRemittance", back_populates="orders")
