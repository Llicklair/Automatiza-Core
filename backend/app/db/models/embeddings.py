import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # FK a tenant_documents con ON DELETE CASCADE: al borrar un documento sus
    # embeddings se eliminan en la BD, en CUALQUIER vía de borrado. Antes era un
    # String sin FK → embeddings huérfanos y el RAG servía chunks de documentos
    # ya borrados.
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(UUID(as_uuid=True), index=True, nullable=False)

    # NULL = base de conocimiento del tenant (visible para todos los empleados).
    # Valor = embedding privado del empleado (sólo si knowledge_enabled).
    employee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    chunk_index = Column(String, nullable=False)  # Para mantener el orden original de los trozos
    text_content = Column(Text, nullable=False)  # El texto extraído

    # Metadata de OpenDataLoader (nullable para compatibilidad con datos existentes)
    page_number = Column(Integer, nullable=True)  # Página de origen en el PDF
    element_type = Column(String, nullable=True)  # paragraph, table, heading, etc.
    bounding_box = Column(JSONB, nullable=True)  # [left, bottom, right, top]

    # Jurisdicción del tenant al momento de indexar (para filtro cross-border)
    jurisdiction = Column(String(20), nullable=True, index=True)

    # Embedding vector almacenado como lista de floats en JSONB.
    # Antes era pgvector.sqlalchemy.Vector(768), pero la app desktop
    # distribuye un Postgres portable sin la extensión pgvector. Para
    # mantenerla portable usamos JSONB y calculamos similitud coseno
    # en Python — adecuado hasta ~5.000 chunks por tenant.
    embedding = Column(JSONB, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
