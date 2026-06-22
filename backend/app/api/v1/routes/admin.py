"""Endpoints de administración: backup y restauración de la base de datos.

Nota de seguridad (auditoría H15): estos endpoints lanzan subprocesos
(pg_dump/psql) pero están acotados:
  - Solo rol admin (`require_role("admin")`) y rate-limit.
  - `create_subprocess_exec` sin shell; los argumentos derivan únicamente
    de `settings.DATABASE_URL` (config del servidor), nunca de input del
    usuario. El único input externo (el .sql de restore) va por stdin a
    psql, que es justamente el propósito del endpoint.
  - Pensados para la app desktop local (Postgres portable del propio
    usuario), no para un despliegue multi-tenant expuesto.
"""

import asyncio
import logging
import re
import urllib.parse
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import require_role
from app.db.base import get_db
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
async def download_backup(
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Genera un pg_dump y lo devuelve como descarga .sql. Solo admin."""
    # El backup usa pg_dump: solo aplica a PostgreSQL (la BD real del desktop).
    # En entornos sin Postgres (p. ej. el SQLite de los tests) es una dependencia
    # no disponible → 503, no 500. Evita además que pg_dump intente conectar a un
    # localhost ajeno y devuelva un 500 confuso ("fe_sendauth: no password").
    if not settings.DATABASE_URL.lower().startswith("postgres"):
        raise HTTPException(
            status_code=503,
            detail="El backup requiere una base de datos PostgreSQL.",
        )
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
    except TimeoutError:
        raise HTTPException(status_code=504, detail="pg_dump tardó demasiado (timeout 120s)")
    except FileNotFoundError:
        # Dependencia ausente (no es un crash del servidor) → 503, no 500.
        raise HTTPException(status_code=503, detail="pg_dump no está disponible en el servidor")

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
    current_user: User = Depends(require_role("admin")),
):
    """Restaura la BD a partir de un archivo .sql subido. Solo admin.
    Operación destructiva: pierde los datos actuales."""
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
    except TimeoutError:
        raise HTTPException(
            status_code=504, detail="La restauración tardó demasiado (timeout 5min)"
        )
    except FileNotFoundError:
        # Dependencia ausente (no es un crash del servidor) → 503, no 500.
        raise HTTPException(status_code=503, detail="psql no está disponible en el servidor")

    if proc.returncode != 0:
        err = stderr.decode(errors="ignore")[:500]
        logger.error("psql restore error: %s", err)
        raise HTTPException(status_code=500, detail=f"Error al restaurar: {err}")

    logger.info("Base de datos restaurada por usuario %s", current_user.email)
    return {"ok": True, "message": "Base de datos restaurada correctamente"}


# ── LLM cache invalidation ────────────────────────────────────────────────────


@router.delete("/llm-cache")
@limiter.limit("10/minute")
async def invalidate_llm_cache(
    request: Request,
    prefix: str = "classify:",
    current_user: User = Depends(require_role("admin")),
):
    """Invalida entradas del cache LLM por prefijo de intent.

    Default ``prefix=classify:`` purga las clasificaciones del orquestador
    (útil tras tocar ``_KEYWORD_MAP`` o ``_STRONG_KEYWORDS`` sin esperar al TTL).
    Pasar ``?prefix=plan:`` para purgar las decomposiciones del planner, etc.
    Solo admin.
    """
    from app.services.llm_cache import llm_cache

    removed = await llm_cache.flush_prefix(prefix)
    logger.info(
        "LLM cache invalidado por admin %s: prefix=%r entradas=%d",
        current_user.email, prefix, removed,
    )
    return {"ok": True, "prefix": prefix, "removed": removed}


# ── DB migration status ─────────────────────────────────────────────────────────


@router.get("/db-status")
@limiter.limit("30/minute")
async def db_status(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Revisión actual de Alembic vs. head esperado (detección de drift).

    Permite detectar desde fuera si la BD quedó atascada en una migración vieja
    (p. ej. un ``alembic upgrade head`` que abortó en el arranque del desktop sin
    avisar — ver lessons.md 2026-05-20). ``up_to_date=False`` ⇒ faltan migraciones.
    """
    # Revisión actual (tabla alembic_version). Puede no existir si la BD aún no se
    # ha inicializado → lo tratamos como "sin revisión", no como error 500.
    current: str | None = None
    try:
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        current = result.scalar_one_or_none()
    except Exception as e:
        logger.warning("db-status: no se pudo leer alembic_version: %s", e)

    # Head esperado, derivado de los scripts versionados (independiente del cwd).
    head: str | None = None
    try:
        from pathlib import Path

        from alembic.config import Config
        from alembic.script import ScriptDirectory

        import app.db

        cfg = Config()
        cfg.set_main_option(
            "script_location", str(Path(app.db.__file__).resolve().parent / "migrations")
        )
        head = ScriptDirectory.from_config(cfg).get_current_head()
    except Exception as e:
        logger.warning("db-status: no se pudo resolver el head de Alembic: %s", e)

    return {
        "current_revision": current,
        "head_revision": head,
        "up_to_date": bool(current) and current == head,
    }
