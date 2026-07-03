"""Registro y estado de backups locales (BAK.LOC + BAK.VF + BAK.UI).

El dump físico lo hace `desktop/postgres-manager.js` con `pg_dump` portable.
El backend solo:
1. Registra metadatos del backup (`record_backup`).
2. Consulta el último backup por tipo (`get_last_backup`).
3. Indica si procede mostrar banner de aviso (`backup_status_for_banner`).

La política de aviso (BAK.UI): banner si `last_backup_at < now() - 7d` para
backup `full`. No bloqueante — el cliente puede dismissir.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.backup import BackupRecord

BackupKind = Literal["full"]

BACKUP_STALE_THRESHOLD_DAYS = 7


def compute_file_sha256(data: bytes) -> str:
    """Calcula SHA-256 hex del contenido del backup para verificar integridad."""
    return hashlib.sha256(data).hexdigest()


async def record_backup(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    kind: BackupKind,
    destination_path: str,
    size_bytes: int,
    sha256_hex: str,
    encryption_key_label: str,
    note: str | None = None,
) -> BackupRecord:
    """Persiste un registro de backup recién realizado.

    `encryption_key_label` distingue qué clave se usó (`user_master`, etc.)
    — útil para reset/auditoría posterior.
    """
    record = BackupRecord(
        tenant_id=tenant_id,
        kind=kind,
        destination_path=destination_path,
        size_bytes=size_bytes,
        sha256_hex=sha256_hex,
        encryption_key_label=encryption_key_label,
        note=note,
    )
    db.add(record)
    await db.flush()
    return record


async def get_last_backup(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    kind: BackupKind | None = None,
) -> BackupRecord | None:
    """Devuelve el último backup del tenant (o por tipo si se especifica)."""
    stmt = select(BackupRecord).where(BackupRecord.tenant_id == tenant_id)
    if kind is not None:
        stmt = stmt.where(BackupRecord.kind == kind)
    stmt = stmt.order_by(desc(BackupRecord.created_at)).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def backup_status_for_banner(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    now: datetime | None = None,
    threshold_days: int = BACKUP_STALE_THRESHOLD_DAYS,
) -> dict:
    """Devuelve estado para el banner UI BAK.UI.

    Output:
        {
          "has_any_backup": bool,
          "last_full_backup_at": ISO | null,
          "stale": bool,           # True si último full > threshold_days
          "show_banner": bool,     # True si stale o no hay backup
          "days_since_last": int | null
        }
    """
    now_ts = now or datetime.now(UTC)
    last_full = await get_last_backup(db, tenant_id=tenant_id, kind="full")

    last_full_at = last_full.created_at if last_full else None
    days_since = None
    stale = False
    if last_full_at is not None:
        # Asegurar tz awareness antes de restar
        if last_full_at.tzinfo is None:
            last_full_at = last_full_at.replace(tzinfo=UTC)
        days_since = (now_ts - last_full_at).days
        stale = days_since > threshold_days

    has_any = last_full is not None
    show_banner = not has_any or stale

    return {
        "has_any_backup": has_any,
        "last_full_backup_at": last_full.created_at.isoformat() if last_full else None,
        "stale": stale,
        "show_banner": show_banner,
        "days_since_last": days_since,
        "threshold_days": threshold_days,
    }
