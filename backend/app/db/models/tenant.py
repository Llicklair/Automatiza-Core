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
    active_llm_provider = Column(String(50), nullable=False, default="claude_code")
    active_embeddings_provider = Column(String(50), nullable=False, default="local")
    # JSON cifrado: { "anthropic": {"api_key": "...", "model": "...", "enabled": true}, ... }
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

    # Procedencia y enlace a la entidad del ERP que el documento refleja.
    # source="generated"  → artefacto que genera el propio ERP (PDF de factura,
    #   nómina, informe). NO debe reimportarse como dato nuevo.
    # source="uploaded"   → documento externo (escaneo, subida) que SÍ puede
    #   asimilarse al ERP.
    # entity_type/entity_id → vínculo opaco a la entidad reflejada o creada a
    #   partir del documento (p.ej. "invoice" + id). Permite mostrar el reflejo
    #   y que la asimilación automática salte lo ya procesado (idempotencia).
    source = Column(String(20), nullable=False, default="uploaded", index=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True))

    locked_by = Column(UUID(as_uuid=True), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)


class TenantOnboarding(Base):
    """Estado del wizard de onboarding focado (UI.ONB).

    Un registro por tenant. 5 pasos booleanos + timestamps. La FSM no es
    estricta — los pasos pueden completarse en cualquier orden o saltarse.
    """

    __tablename__ = "tenant_onboarding"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    step_company = Column(Boolean, nullable=False, default=False)
    step_cert = Column(Boolean, nullable=False, default=False)
    step_data = Column(Boolean, nullable=False, default=False)
    step_use_case = Column(Boolean, nullable=False, default=False)
    # BYOK: el usuario configura su clave de IA (proveedor + api_key). Se
    # auto-marca desde la readiness real del tenant (ver wizard.sync_llm_config_step).
    step_llm_config = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    skipped_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class AutonomyPolicy(Base):
    """Política de autonomía por dominio (SEC.AUT).

    Mode ∈ {AUTO, CONFIRM, MANUAL}. La ausencia de fila equivale al default
    del dominio (ver `services/autonomy.py:DEFAULTS`).
    """

    __tablename__ = "autonomy_policy"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    domain = Column(String(64), nullable=False)
    mode = Column(String(16), nullable=False)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
