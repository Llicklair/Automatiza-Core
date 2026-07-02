"""Backups automáticos de la base de datos del usuario.

Para single-tenant desktop, perder la BD = perder toda la PYME. Este módulo
genera un dump diario de Postgres en formato `custom` (binario, comprimido,
restaurable selectivamente con `pg_restore`) y aplica rotación.

Diseño:
- Ejecuta `pg_dump --format=custom` como subprocess para no depender de
  bibliotecas Python específicas del driver.
- Localiza `pg_dump` por PATH primero, luego por la ruta conocida del
  Postgres portable que arranca `desktop/postgres-manager.js`.
- Autentica vía PGPASSWORD env var (no se loguea, no aparece en `ps`).
- Rotación: borra backups con mtime > BACKUP_RETENTION_DAYS.
- Si falla, registra el error pero NO levanta — el scheduler no debe
  pararse por un disco lleno o pg_dump caído.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings
from app.core.paths import app_data_dir

logger = logging.getLogger(__name__)


def _default_backup_dir() -> Path:
    """Directorio de backups dentro del data dir de la app (`…/backups`)."""
    return app_data_dir("backups")


def _portable_postgres_bin() -> Path | None:
    """Devuelve el path al directorio bin del Postgres portable que gestiona
    la app desktop, o None si no existe."""
    candidate = app_data_dir("pgsql", "bin")
    return candidate if candidate.exists() else None


def _find_pg_dump() -> Path | None:
    """Busca `pg_dump` en PATH y en el bin del Postgres portable de la app."""
    exe = "pg_dump.exe" if sys.platform == "win32" else "pg_dump"

    found = shutil.which(exe)
    if found:
        return Path(found)

    portable_bin = _portable_postgres_bin()
    if portable_bin:
        candidate = portable_bin / exe
        if candidate.exists():
            return candidate

    return None


def _parse_db_url(url: str) -> dict[str, str | int]:
    """Extrae host, port, dbname, user, password de una URL postgresql+asyncpg."""
    # Normaliza driver: postgresql+asyncpg://... → postgresql://...
    normalized = url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    parsed = urlparse(normalized)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "dbname": parsed.path.lstrip("/") or "postgres",
        "user": parsed.username or "",
        "password": parsed.password or "",
    }


async def create_backup(backup_dir: Path | None = None) -> Path | None:
    """Genera un dump custom-format de la BD configurada en DATABASE_URL.

    Devuelve el Path del archivo creado, o None si falló (loggeado).
    """
    pg_dump = _find_pg_dump()
    if pg_dump is None:
        logger.warning("backup: pg_dump no encontrado en PATH ni en el Postgres portable. Skip.")
        return None

    target_dir = backup_dir or Path(settings.BACKUP_DIR or _default_backup_dir())
    target_dir.mkdir(parents=True, exist_ok=True)

    db = _parse_db_url(settings.DATABASE_URL)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_file = target_dir / f"{db['dbname']}_{timestamp}.dump"

    cmd = [
        str(pg_dump),
        "--host",
        str(db["host"]),
        "--port",
        str(db["port"]),
        "--username",
        str(db["user"]),
        "--dbname",
        str(db["dbname"]),
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(out_file),
    ]

    env = {**os.environ, "PGPASSWORD": str(db["password"])}
    start = time.monotonic()

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
    except TimeoutError:
        logger.error("backup: pg_dump excedió 10 min y fue cancelado")
        if out_file.exists():
            out_file.unlink(missing_ok=True)
        return None
    except Exception as exc:
        logger.error("backup: error invocando pg_dump: %s", exc)
        return None

    if proc.returncode != 0:
        err_text = (stderr or b"").decode(errors="replace")[:500]
        logger.error("backup: pg_dump falló (rc=%s): %s", proc.returncode, err_text)
        if out_file.exists():
            out_file.unlink(missing_ok=True)
        return None

    duration = time.monotonic() - start
    size_mb = out_file.stat().st_size / (1024 * 1024)
    logger.info("backup: %s (%.1f MB en %.1fs)", out_file.name, size_mb, duration)
    return out_file


def rotate_backups(
    backup_dir: Path | None = None,
    retention_days: int | None = None,
) -> int:
    """Borra dumps con mtime más viejo que retention_days. Devuelve nº borrados."""
    target_dir = backup_dir or Path(settings.BACKUP_DIR or _default_backup_dir())
    if not target_dir.exists():
        return 0

    days = retention_days if retention_days is not None else settings.BACKUP_RETENTION_DAYS
    cutoff = datetime.now(UTC) - timedelta(days=days)
    cutoff_ts = cutoff.timestamp()

    deleted = 0
    for entry in target_dir.glob("*.dump"):
        try:
            if entry.stat().st_mtime < cutoff_ts:
                entry.unlink()
                deleted += 1
        except OSError as exc:
            logger.warning("backup: no se pudo borrar %s: %s", entry, exc)

    if deleted:
        logger.info("backup: rotación borró %d dumps > %dd", deleted, days)
    return deleted


async def run_backup_job() -> dict[str, int | str | None]:
    """Punto de entrada para APScheduler: backup + rotación.

    Devuelve un dict con metadata útil para tests/manual invocation.
    """
    if not settings.BACKUP_ENABLED:
        logger.info("backup: deshabilitado por config (BACKUP_ENABLED=false). Skip.")
        return {"created": None, "rotated": 0, "status": "disabled"}

    created = await create_backup()
    rotated = rotate_backups()
    return {
        "created": str(created) if created else None,
        "rotated": rotated,
        "status": "ok" if created else "failed",
    }


# ── API helpers (usados por routes/system.py) ────────────────────────────────


def _backup_dir() -> Path:
    """Devuelve el directorio efectivo de backups (config o default por OS)."""
    return Path(settings.BACKUP_DIR or _default_backup_dir())


def _resolve_safe(filename: str) -> Path:
    """Resuelve un nombre de archivo dentro del backup_dir, bloqueando path
    traversal. Lanza ValueError si el path resuelto se escapa del directorio
    o no es un .dump."""
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError(f"Nombre de archivo inválido: {filename!r}")
    if not filename.endswith(".dump"):
        raise ValueError("Solo se permiten archivos .dump")

    base = _backup_dir().resolve()
    target = (base / filename).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"Path fuera del directorio de backups: {filename!r}") from exc
    return target


def list_backups() -> list[dict[str, Any]]:
    """Lista los backups disponibles ordenados por mtime descendente."""
    base = _backup_dir()
    if not base.exists():
        return []

    items: list[dict[str, Any]] = []
    for entry in base.glob("*.dump"):
        try:
            stat = entry.stat()
        except OSError:
            continue
        items.append(
            {
                "filename": entry.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                "age_hours": round((time.time() - stat.st_mtime) / 3600, 1),
            }
        )
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items


def get_backup_path(filename: str) -> Path:
    """Devuelve el Path absoluto a un backup, validando que existe.
    Lanza FileNotFoundError o ValueError según el caso."""
    target = _resolve_safe(filename)
    if not target.exists():
        raise FileNotFoundError(f"Backup no encontrado: {filename}")
    return target


def delete_backup(filename: str) -> bool:
    """Borra un backup específico. Devuelve True si se borró, False si no existía."""
    try:
        target = _resolve_safe(filename)
    except ValueError:
        raise
    if not target.exists():
        return False
    target.unlink()
    logger.info("backup: borrado manualmente %s", filename)
    return True


def _find_pg_restore() -> Path | None:
    """Equivalente a _find_pg_dump para pg_restore (mismo dir bin)."""
    exe = "pg_restore.exe" if sys.platform == "win32" else "pg_restore"
    found = shutil.which(exe)
    if found:
        return Path(found)
    portable_bin = _portable_postgres_bin()
    if portable_bin:
        candidate = portable_bin / exe
        if candidate.exists():
            return candidate
    return None


async def restore_backup(filename: str) -> dict[str, str | None]:
    """Restaura la BD desde un backup. OPERACIÓN DESTRUCTIVA: --clean borra
    los objetos existentes antes de recrearlos.

    Devuelve {"status": "ok"|"failed", "error": str|None}.
    """
    target = get_backup_path(filename)  # valida existencia y path

    pg_restore = _find_pg_restore()
    if pg_restore is None:
        return {"status": "failed", "error": "pg_restore no encontrado en PATH ni en Postgres portable"}

    db = _parse_db_url(settings.DATABASE_URL)
    cmd = [
        str(pg_restore),
        "--host",
        str(db["host"]),
        "--port",
        str(db["port"]),
        "--username",
        str(db["user"]),
        "--dbname",
        str(db["dbname"]),
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        str(target),
    ]
    env = {**os.environ, "PGPASSWORD": str(db["password"])}

    logger.warning("backup: RESTORE iniciado desde %s — operación destructiva", filename)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=900)
    except TimeoutError:
        return {"status": "failed", "error": "pg_restore excedió 15 min"}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)[:500]}

    if proc.returncode != 0:
        err_text = (stderr or b"").decode(errors="replace")[:500]
        logger.error("backup: pg_restore falló (rc=%s): %s", proc.returncode, err_text)
        return {"status": "failed", "error": err_text}

    logger.info("backup: RESTORE completado desde %s", filename)
    return {"status": "ok", "error": None}
