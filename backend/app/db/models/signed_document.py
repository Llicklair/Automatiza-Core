"""Modelo de documento firmado vía AutoFirma del Estado (F3.11)."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base
from app.db.models.common import utcnow


class SignedDocument(Base):
    __tablename__ = "signed_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_token = Column(String(64), nullable=False, unique=True)
    signature_format = Column(String(20), nullable=False)  # PAdES | XAdES | CAdES
    status = Column(String(20), nullable=False, default="pending")  # pending|signed|failed
    original_hash = Column(String(64), nullable=False)
    signed_hash = Column(String(64), nullable=True)
    signer_nif = Column(String(32), nullable=True)
    signer_cn = Column(String(255), nullable=True)
    issuer_cn = Column(String(255), nullable=True)
    tsa_url = Column(String(255), nullable=True)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
