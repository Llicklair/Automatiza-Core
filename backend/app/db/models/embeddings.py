import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(String, index=True, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    
    chunk_index = Column(String, nullable=False)  # Para mantener el orden original de los trozos
    text_content = Column(Text, nullable=False)   # El texto extraído
    
    # Vector column. Llama 3.2 nomic-embed-text generates 768-dimensional vectors.
    embedding = Column(Vector(768), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
