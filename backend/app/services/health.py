"""Health checks adicionales: Redis, APScheduler, último backup.

Cada función devuelve un dict {"status": "up|down|unknown|disabled", ...}
y nunca lanza — los problemas se reportan vía el campo `error`. El
endpoint /health agrega estos en `health["checks"]`.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings


async def check_redis(timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Pingea Redis si REDIS_URL está configurado. Si no, status="disabled"."""
    if not settings.REDIS_URL:
        return {"status": "disabled"}

    try:
        from redis import asyncio as aioredis

        client = aioredis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds,
        )
        t0 = time.perf_counter()
        try:
            await asyncio.wait_for(client.ping(), timeout=timeout_seconds)
        finally:
            await client.aclose()
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"status": "up", "latency_ms": latency_ms}
    except Exception as exc:
        return {"status": "down", "error": str(exc)[:200]}


def check_scheduler() -> dict[str, Any]:
    """Reporta si el AsyncIOScheduler está corriendo y cuántos jobs tiene."""
    try:
        from app.services.scheduler import scheduler

        if not scheduler.running:
            return {"status": "down", "running": False}
        jobs = scheduler.get_jobs()
        next_runs = sorted(
            [j.next_run_time for j in jobs if j.next_run_time is not None]
        )
        return {
            "status": "up",
            "running": True,
            "jobs": len(jobs),
            "next_run": next_runs[0].isoformat() if next_runs else None,
        }
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)[:200]}


def check_last_backup() -> dict[str, Any]:
    """Devuelve metadata del backup más reciente o {disabled, never} si aplica."""
    if not settings.BACKUP_ENABLED:
        return {"status": "disabled"}

    from app.services.backup import _default_backup_dir  # noqa: PLC0415

    target = Path(settings.BACKUP_DIR or _default_backup_dir())
    if not target.exists():
        return {"status": "never", "path": str(target)}

    dumps = sorted(target.glob("*.dump"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not dumps:
        return {"status": "never", "path": str(target)}

    latest = dumps[0]
    stat = latest.stat()
    age_hours = (time.time() - stat.st_mtime) / 3600
    return {
        "status": "ok",
        "file": latest.name,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "age_hours": round(age_hours, 1),
        "created_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
        "total_dumps": len(dumps),
    }
