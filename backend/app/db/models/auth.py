"""Modelos de autenticación y tenancy."""

from .common import (
    UUID,
    Base,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    relationship,
    utcnow,
    uuid,
    Text,
)


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    nif = Column(String(9), unique=True, nullable=False, index=True)
    address = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    contact_email = Column(String(255), nullable=True)
    plan = Column(String(50), nullable=False, default="starter")
    is_active = Column(Boolean, default=True, nullable=False)
    ui_locale = Column(
        String(10), nullable=False, default="es-ES"
    )  # Consumido por next-intl en frontend
    jurisdiction = Column(
        String(20), nullable=False, default="ES_TAX"
    )  # Consumido por RAG retriever filter
    # Firma digital (certificado PKCS#12 para XAdES-BES)
    cert_path = Column(String(500), nullable=True)
    cert_password = Column(Text, nullable=True)
    cert_subject = Column(String(500), nullable=True)
    cert_expires_at = Column(DateTime(timezone=True), nullable=True)
    # Logo corporativo del tenant — usado por agent_report.py en informes PDF
    logo_path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    users = relationship("User", back_populates="tenant")
    tasks = relationship("Task", back_populates="tenant")
    domain_events = relationship("DomainEvent", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200))
    role = Column(String(50), nullable=False, default="user")  # admin|user|viewer|employee
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_login_at = Column(DateTime(timezone=True))

    tenant = relationship("Tenant", back_populates="users")


class ClientPortalToken(Base):
    """Token de acceso de cliente al portal externo."""
    __tablename__ = "client_portal_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 del token bruto
    is_active = Column(Boolean, nullable=False, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 del token
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class UserInvitation(Base):
    """Invitación de acceso al tenant. El admin genera una y comparte el enlace; el invitado pone su contraseña al aceptar."""
    __tablename__ = "user_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="employee")  # admin|user|employee
    token_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 del token bruto
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    used_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
