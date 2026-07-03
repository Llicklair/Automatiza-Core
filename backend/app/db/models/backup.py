"""Modelo de registro de backups locales (BAK.LOC)."""

from .common import (
    UUID,
    Base,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    utcnow,
)


class BackupRecord(Base):
    """Append-only — registro de cada backup local realizado.

    Tipos (`kind`):
    * `full` — pg_dump completo cifrado con clave maestra del usuario.

    Append-only enforced en Postgres (migración 0017 triggers).
    """

    __tablename__ = "backup_record"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    kind = Column(String(20), nullable=False)  # "full"
    destination_path = Column(String(1000), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    sha256_hex = Column(String(64), nullable=False)
    encryption_key_label = Column(String(50), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
