"""Endpoints de administración: backup y restauración de la base de datos."""

import asyncio
import logging
import re
import urllib.parse
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.models.models import User
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _parse_db_url(url: str) -> dict:
    """Extrae host, port, user, password y dbname de DATABASE_URL."""
    # Normaliza asyncpg → psycopg2 scheme para parsear
    clean = url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    parsed = urllib.parse.urlparse(clean)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": urllib.parse.unquote(parsed.username or ""),
        "password": urllib.parse.unquote(parsed.password or ""),
        "dbname": parsed.path.lstrip("/"),
    }


# ── Backup ─────────────────────────────────────────────────────────────────────


@router.get("/backup")
@limiter.limit("10/minute")
async def download_backup(request: Request, current_user: User = Depends(get_current_user)):
    """Genera un pg_dump y lo devuelve como descarga .sql."""
    db_info = _parse_db_url(settings.DATABASE_URL)

    env = {"PGPASSWORD": db_info["password"]}
    cmd = [
        "pg_dump",
        "-h",
        db_info["host"],
        "-p",
        db_info["port"],
        "-U",
        db_info["user"],
        "-d",
        db_info["dbname"],
        "--no-password",
        "--clean",
        "--if-exists",
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**__import__("os").environ, **env},
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="pg_dump tardó demasiado (timeout 120s)")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="pg_dump no está disponible en el servidor")

    if proc.returncode != 0:
        logger.error("pg_dump error: %s", stderr.decode())
        raise HTTPException(status_code=500, detail="Error al generar el backup")

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.sql"

    return StreamingResponse(
        iter([stdout]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Restore ────────────────────────────────────────────────────────────────────


@router.post("/restore")
@limiter.limit("10/minute")
async def restore_backup(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Restaura la BD a partir de un archivo .sql subido por el usuario."""
    if not file.filename or not file.filename.lower().endswith(".sql"):
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .sql")

    # Límite 100 MB
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo supera los 100 MB permitidos")

    # Validación mínima: debe contener SQL típico de pg_dump
    snippet = content[:2048].decode("utf-8", errors="ignore")
    if not re.search(r"(PostgreSQL|SET|CREATE|INSERT|COPY|--)", snippet):
        raise HTTPException(
            status_code=400, detail="El archivo no parece un backup de PostgreSQL válido"
        )

    db_info = _parse_db_url(settings.DATABASE_URL)
    env = {"PGPASSWORD": db_info["password"]}
    cmd = [
        "psql",
        "-h",
        db_info["host"],
        "-p",
        db_info["port"],
        "-U",
        db_info["user"],
        "-d",
        db_info["dbname"],
        "--no-password",
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**__import__("os").environ, **env},
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(input=content), timeout=300)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, detail="La restauración tardó demasiado (timeout 5min)"
        )
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="psql no está disponible en el servidor")

    if proc.returncode != 0:
        err = stderr.decode(errors="ignore")[:500]
        logger.error("psql restore error: %s", err)
        raise HTTPException(status_code=500, detail=f"Error al restaurar: {err}")

    logger.info("Base de datos restaurada por usuario %s", current_user.email)
    return {"ok": True, "message": "Base de datos restaurada correctamente"}
