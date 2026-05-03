"""System routes — frontend error reporting, diagnostics, backups."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.dependencies import require_role
from app.services import backup as backup_service

router = APIRouter(prefix="/system", tags=["system"])
logger = logging.getLogger("frontend_errors")


class FrontendError(BaseModel):
    message: str = Field(..., max_length=2000)
    stack: str | None = Field(None, max_length=5000)
    url: str | None = Field(None, max_length=500)
    component: str | None = Field(None, max_length=200)
    digest: str | None = Field(None, max_length=100)
    timestamp: str | None = None


@router.post("/frontend-errors", status_code=204)
async def report_frontend_error(payload: FrontendError, request: Request):
    """Receive and log errors from the frontend error boundaries."""
    logger.warning(
        "FRONTEND_ERROR component=%s url=%s message=%s digest=%s",
        payload.component or "unknown",
        payload.url or "-",
        payload.message[:200],
        payload.digest or "-",
    )
    if payload.stack:
        logger.debug("FRONTEND_ERROR_STACK:\n%s", payload.stack[:3000])
    return None


# ── Backups ──────────────────────────────────────────────────────────────────
# Acceso restringido a admin: borrar o restaurar destruye datos del tenant.

_admin_only = Depends(require_role("admin"))


class BackupItem(BaseModel):
    filename: str
    size_mb: float
    created_at: str
    age_hours: float


class RestoreResult(BaseModel):
    status: str
    error: str | None = None


class RunBackupResult(BaseModel):
    created: str | None
    rotated: int
    status: str


@router.get("/backups", response_model=list[BackupItem], dependencies=[_admin_only])
async def list_backups_endpoint() -> list[dict]:
    """Lista los backups disponibles, más recientes primero."""
    return backup_service.list_backups()


@router.post("/backups", response_model=RunBackupResult, dependencies=[_admin_only])
async def run_backup_endpoint() -> dict:
    """Ejecuta un backup manual (además del job diario automático)."""
    return await backup_service.run_backup_job()


@router.get("/backups/{filename}/download", dependencies=[_admin_only])
async def download_backup_endpoint(filename: str):
    """Descarga el archivo .dump para guardarlo fuera del equipo."""
    try:
        path = backup_service.get_backup_path(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return FileResponse(
        path=path,
        filename=filename,
        media_type="application/octet-stream",
    )


@router.post(
    "/backups/{filename}/restore",
    response_model=RestoreResult,
    dependencies=[_admin_only],
)
async def restore_backup_endpoint(filename: str):
    """OPERACIÓN DESTRUCTIVA: restaura la BD desde un backup. Borra los
    objetos existentes antes de recrearlos. Asegúrate de tener el backup
    actual descargado antes de invocar."""
    try:
        return await backup_service.restore_backup(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete(
    "/backups/{filename}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin_only],
)
async def delete_backup_endpoint(filename: str):
    """Borra un backup específico de disco."""
    try:
        deleted = backup_service.delete_backup(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Backup no encontrado: {filename}")
    return None
