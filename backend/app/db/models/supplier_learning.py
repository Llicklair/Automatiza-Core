"""Modelos para aprendizaje OCR por proveedor (F2.5).

Dos tablas que reducen consumo LLM en facturas recurrentes:

  - `InvoiceScanCache`         — dedupe SHA-256 → re-uso directo de la
                                  extracción anterior cuando el PDF entra
                                  por segunda vez.
  - `SupplierInvoiceTemplate`  — memoria por NIF (overrides del usuario,
                                  última extracción para few-shot,
                                  estadísticas).
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base
from app.db.models.common import utcnow


class InvoiceScanCache(Base):
    __tablename__ = "invoice_scan_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_hash = Column(String(64), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(50), nullable=False)
    extracted_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class SupplierInvoiceTemplate(Base):
    __tablename__ = "supplier_invoice_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_nif = Column(String(32), nullable=False)
    supplier_name = Column(String(255), nullable=True)
    default_tax_percentage = Column(Numeric(5, 2), nullable=True)
    description_overrides = Column(JSONB, nullable=True)  # {pattern: replacement}
    last_extraction = Column(JSONB, nullable=True)
    extractions_count = Column(Integer, nullable=False, default=0)
    avg_amount_total = Column(Numeric(12, 2), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
