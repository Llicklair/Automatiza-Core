import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(String, index=True, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    
    chunk_index = Column(String, nullable=False)  # Para mantener el orden original de los trozos
    text_content = Column(Text, nullable=False)   # El texto extraído

    # Metadata de OpenDataLoader (nullable para compatibilidad con datos existentes)
    page_number = Column(Integer, nullable=True)       # Página de origen en el PDF
    element_type = Column(String, nullable=True)       # paragraph, table, heading, etc.
    bounding_box = Column(JSONB, nullable=True)        # [left, bottom, right, top]

    # Vector column — 768-dimensional (BAAI/bge-m3)
    embedding = Column(Vector(768), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
