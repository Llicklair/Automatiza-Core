"""System routes — frontend error reporting, diagnostics, backups."""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.base import get_db
from app.db.models.auth import User
from app.services import backup as backup_service
from app.services.system.diagnostic_bundle import build_diagnostic_bundle
from app.services.system.preconditions import check_invoice_preconditions

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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        path=path,
        filename=filename,
        media_type="application/octet-stream",
    )


# Mutex de proceso: dos pg_restore concurrentes sobre la misma BD la corrompen.
# El caso real: el usuario lanza la restauración, navega (pierde el indicador
# local de "restaurando") y al volver la relanza sobre el mismo backup.
_restore_lock = asyncio.Lock()


@router.post(
    "/backups/{filename}/restore",
    response_model=RestoreResult,
    dependencies=[_admin_only],
)
async def restore_backup_endpoint(filename: str):
    """OPERACIÓN DESTRUCTIVA: restaura la BD desde un backup. Borra los
    objetos existentes antes de recrearlos. Asegúrate de tener el backup
    actual descargado antes de invocar."""
    if _restore_lock.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya hay una restauración en curso. Espera a que termine.",
        )
    async with _restore_lock:
        try:
            return await backup_service.restore_backup(filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Backup no encontrado: {filename}")
    return None


# ── CONT.KILL — kill-switch de precondiciones legales ──────────────────────


@router.get("/preconditions", dependencies=[_admin_only])
async def get_invoice_preconditions(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Devuelve el estado de las precondiciones legales para facturación (CONT.KILL).

    Verifica tablas críticas: `invoice_series` (FAC.NUM) y `fiscal_approval_log`
    (SEC.APR). Si falta alguna, las rutas de creación de factura deben rechazar
    POST con 503.
    """
    return await check_invoice_preconditions(db)


async def require_invoice_preconditions(
    db: AsyncSession = Depends(get_db),
) -> None:
    """Dependency inyectable en POST /invoices y similar.

    Rechaza con HTTP 503 si alguna precondición legal falta. Esto previene
    emitir facturas que no serían defendibles ante AEAT/inspección.
    """
    status_check = await check_invoice_preconditions(db)
    if not status_check["ok"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "invoice_preconditions_failed",
                "message": (
                    "El sistema no cumple las precondiciones legales mínimas "
                    "para emitir facturas. Faltan tablas críticas — "
                    "ejecutar `alembic upgrade head`."
                ),
                "missing": status_check["missing"],
            },
        )


# ── CONT.LOG — bundle de diagnóstico exportable ────────────────────────────


@router.get("/diagnostic-bundle")
async def get_diagnostic_bundle(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Genera un ZIP con logs scrubbed + info de versión + esquema actual.

    Diseñado para soporte L1/L2: el cliente lo descarga y lo envía sin
    revelar PII. Los logs ya están scrubbed por `JSONFormatter`. El bundle
    contiene logs COMPLETOS del servidor → solo admin (coherente con
    /backups/*); require_role("admin") gatea y devuelve el User autenticado.
    """
    zip_bytes = await build_diagnostic_bundle(db)
    filename = f"automatizacore-diagnostic-{user.tenant_id}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
