"""Bundle de diagnóstico (CONT.LOG).

Empaqueta en un ZIP:
- Logs JSON recientes (últimos N archivos rotados).
- `info.json` con versión, Python version, OS, plataforma, fecha de generación.
- `precondiciones.json` con estado de tablas críticas (CONT.KILL healthcheck).
- `alembic_version.txt` con la migración actual (si BD reachable).

Sin PII: los logs ya están scrubbed por `JSONFormatter`. No se incluyen:
datos de negocio, prompts/outputs en plano, NIFs/IBANs (regex bloqueado),
emails de usuarios, tokens, IPs.
"""

import io
import json
import logging
import os
import platform
import sys
import zipfile
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.structured_logging import get_log_dir
from app.services.system.preconditions import check_invoice_preconditions

logger = logging.getLogger(__name__)


async def build_diagnostic_bundle(db: AsyncSession) -> bytes:
    """Genera un ZIP en memoria con todo el bundle. Devuelve los bytes.

    El ZIP incluye:
        info.json
        precondiciones.json
        alembic_version.txt
        logs/<archivos JSONL existentes>
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # info.json
        info = {
            "generated_at": datetime.now(UTC).isoformat(),
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            "python_version": sys.version,
            "platform": platform.platform(),
            "os_family": (
                "windows" if os.name == "nt"
                else "macos" if sys.platform == "darwin"
                else "linux" if sys.platform.startswith("linux")
                else "other"
            ),
        }
        zf.writestr("info.json", json.dumps(info, indent=2, default=str))

        # precondiciones.json — CONT.KILL healthcheck snapshot
        try:
            precond = await check_invoice_preconditions(db)
        except Exception as e:
            precond = {"ok": False, "error": str(e)[:200]}
        zf.writestr("precondiciones.json", json.dumps(precond, indent=2, default=str))

        # alembic_version.txt
        alembic_version = "unknown"
        try:
            result = await db.execute(text("SELECT version_num FROM alembic_version"))
            row = result.scalar_one_or_none()
            if row:
                alembic_version = row
        except Exception as e:
            alembic_version = f"error: {str(e)[:200]}"
        zf.writestr("alembic_version.txt", alembic_version)

        # logs/*.jsonl
        log_dir = get_log_dir()
        if log_dir.exists():
            for log_file in sorted(log_dir.glob("*.jsonl*")):
                try:
                    zf.write(str(log_file), f"logs/{log_file.name}")
                except OSError:
                    # archivo en uso o sin permisos — omitir y seguir
                    continue

    return buffer.getvalue()
