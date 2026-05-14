"""Endpoints REST de registro de backups locales (BAK.LOC + BAK.UI)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import User
from app.services.backup_local import (
    backup_status_for_banner,
    record_backup,
)


router = APIRouter(prefix="/backup-local", tags=["backup"])


class RecordBackupRequest(BaseModel):
    kind: str = Field(..., pattern="^(full|verifactu)$")
    destination_path: str = Field(..., min_length=1, max_length=1000)
    size_bytes: int = Field(..., ge=0)
    sha256_hex: str = Field(..., min_length=64, max_length=64, pattern="^[0-9a-f]{64}$")
    encryption_key_label: str = Field(..., min_length=1, max_length=50)
    note: str | None = None


class RecordBackupResponse(BaseModel):
    id: int
    tenant_id: str
    kind: str
    destination_path: str
    size_bytes: int
    sha256_hex: str
    created_at: datetime


class BackupStatusResponse(BaseModel):
    has_any_backup: bool
    last_full_backup_at: datetime | None
    last_verifactu_backup_at: datetime | None
    stale: bool
    show_banner: bool
    days_since_last: int | None
    threshold_days: int


@router.post("/record", response_model=RecordBackupResponse, status_code=status.HTTP_201_CREATED)
async def record_backup_endpoint(
    body: RecordBackupRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecordBackupResponse:
    """Registra metadatos de un backup ejecutado por `postgres-manager.js`.

    El cliente Electron llama a este endpoint tras `pg_dump` exitoso con el
    SHA-256 del archivo cifrado. La inmutabilidad la enforza el trigger
    Postgres en migración 0017.
    """
    try:
        record = await record_backup(
            db,
            tenant_id=user.tenant_id,
            kind=body.kind,  # type: ignore[arg-type]
            destination_path=body.destination_path,
            size_bytes=body.size_bytes,
            sha256_hex=body.sha256_hex,
            encryption_key_label=body.encryption_key_label,
            note=body.note,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registrando backup: {e}")

    await db.commit()
    return RecordBackupResponse(
        id=record.id,
        tenant_id=str(record.tenant_id),
        kind=record.kind,
        destination_path=record.destination_path,
        size_bytes=record.size_bytes,
        sha256_hex=record.sha256_hex,
        created_at=record.created_at,
    )


@router.get("/status", response_model=BackupStatusResponse)
async def get_backup_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BackupStatusResponse:
    """Estado actual de backups para mostrar banner UI (BAK.UI)."""
    status_data = await backup_status_for_banner(db, tenant_id=user.tenant_id)
    return BackupStatusResponse(**status_data)
