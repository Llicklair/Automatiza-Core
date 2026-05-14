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


class TelemetryOptOut(Base):
    """Registro de revocación de consentimiento de telemetría (AI.REV).

    Cumplimiento RGPD Art. 17 (derecho de supresión) + Art. 7 (revocabilidad).
    Un tenant aparece aquí cuando un usuario autorizado solicita la
    desactivación de telemetría. La presencia del registro:
    1. Bloquea la generación de nuevos eventos en el cliente.
    2. Programa job de purga en el VPS de eventos con `tenant_id_hash` activo.

    Idempotente: revocar dos veces no es error (el segundo INSERT se ignora
    por UNIQUE en tenant_id).
    """

    __tablename__ = "telemetry_opt_out"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    requested_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class TenantRegapStatus(Base):
    """Estado del apoderamiento REGAP por tenant (PRES.REG).

    Una sola fila por tenant. La FSM avanza:
      not_started → identifying → cert_pending → power_granted → verified
                                                     │
                                                     └→ rejected (excepcional)

    `auth_method` ∈ {clave_pin, clave_permanente, cert_fnmt} — rama elegida
    en el wizard. `verify_payload` guarda el JSON de respuesta de la consulta
    REGAP (opaco hasta FAC.TST contra entorno real AEAT).
    """

    __tablename__ = "tenant_regap_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        index=True,
    )
    status = Column(String(32), nullable=False, default="not_started")
    auth_method = Column(String(32), nullable=True)
    apoderado_nif = Column(String(20), nullable=True)
    apoderado_nombre = Column(String(200), nullable=True)
    verify_payload = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
