"""Modelo de interfaz HTML generada por IA."""

from sqlalchemy import JSON

from .common import UUID, Base, Boolean, Column, DateTime, String, Text, utcnow, uuid


class GeneratedUI(Base):
    """Interfaz HTML generada por IA y anclada como sección permanente.

    La comunicación con el ERP es unidireccional: solo lectura de datos,
    nunca escritura para proteger el monolito.
    """

    __tablename__ = "generated_uis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    prompt = Column(Text, nullable=False)
    content_html = Column(Text, nullable=False)
    is_pinned = Column(Boolean, default=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
