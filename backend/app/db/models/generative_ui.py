"""Modelo de interfaz HTML generada por IA."""

from sqlalchemy import JSON

from .common import UUID, Base, Boolean, Column, DateTime, ForeignKey, String, Text, utcnow, uuid


class GeneratedUI(Base):
    """Interfaz HTML generada por IA y anclada como sección permanente.

    La comunicación con el ERP es unidireccional: solo lectura de datos,
    nunca escritura para proteger el monolito.
    """

    __tablename__ = "generated_uis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    prompt = Column(Text, nullable=False)
    content_html = Column(Text, nullable=False)
    is_pinned = Column(Boolean, default=True)
    metadata_json = Column(JSON, nullable=True)
    # timezone=True: utcnow() devuelve datetime.now(UTC) (aware). Sin esto la columna
    # era naive y asyncpg rechazaba el INSERT en Postgres (mismo bug que hr_documents).
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
