"""Rechazos persistentes de sugerencias de conciliación (F2.6).

Una fila por (tenant_id, transaction_id, invoice_id) descartado por el
usuario. El motor de sugerencias filtra estos pares antes de devolver
candidatos.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.db.models.common import utcnow


class ReconciliationRejection(Base):
    __tablename__ = "reconciliation_rejections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_id = Column(UUID(as_uuid=True), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), nullable=False)
    reason = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
