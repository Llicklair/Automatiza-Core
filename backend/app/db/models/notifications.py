"""Modelos de notificaciones persistentes (UI.NOT)."""

from .common import (
    JSONB,
    UUID,
    Base,
    Column,
    DateTime,
    String,
    Text,
    utcnow,
    uuid,
)


class Notification(Base):
    """Notificación persistida en BD para bandeja cross-session.

    `kind` ∈ {info, success, warning, error}. `read_at` NULL = pendiente.
    `payload` JSONB libre para evolución del esquema.
    """

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    kind = Column(String(32), nullable=False, default="info")
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
