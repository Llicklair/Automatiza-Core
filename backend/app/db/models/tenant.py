"""Modelos de configuración del tenant: integraciones, conocimiento y documentos."""

from .common import (
    JSONB,
    UUID,
    Base,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    utcnow,
    uuid,
)


class TenantIntegration(Base):
    __tablename__ = "tenant_integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    integration_type = Column(String(50), nullable=False)
    encrypted_credentials = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    config = Column(JSONB, default=dict)


class TenantKnowledge(Base):
    __tablename__ = "tenant_knowledge"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    key = Column(String(255), nullable=False, index=True)
    value = Column(Text, nullable=False)
    category = Column(String(50), default="general")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TenantLlmConfig(Base):
    """Configuración LLM por tenant: claves API cifradas + provider activo + toggles."""

    __tablename__ = "tenant_llm_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True, index=True
    )
    # Provider activo para LLM y embeddings
    active_llm_provider = Column(String(50), nullable=False, default="gemini")
    active_embeddings_provider = Column(String(50), nullable=False, default="local")
    # JSON cifrado: { "gemini": {"api_key": "...", "model": "...", "enabled": true}, ... }
    encrypted_keys = Column(Text)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TenantDocument(Base):
    __tablename__ = "tenant_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True)

    file_name = Column(String(500), nullable=False)
    file_type = Column(String(100))
    file_path = Column(Text, nullable=False)
    file_size = Column(BigInteger, default=0)

    status = Column(String(50), nullable=False, default="uploaded", index=True)
    parsed_content = Column(Text)
    category = Column(String(50), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True))

    locked_by = Column(UUID(as_uuid=True), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
