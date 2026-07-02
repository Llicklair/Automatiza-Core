# Copyright © 2026 Marcos Recio <marcosreciosanchez@gmail.com> — AutomatizaCore
# SPDX-License-Identifier: LicenseRef-Proprietary
"""Aplicación principal FastAPI."""

import asyncio
import inspect
import logging
import sys
from contextlib import asynccontextmanager

# Python 3.14+ depreca asyncio.iscoroutinefunction; slowapi 0.1.x aún la usa.
# Debe ir antes de cualquier import de slowapi.
#
# DIS.SHIM (deferred): retirar este shim cuando slowapi publique 1.0 (no existe
# aún en PyPI a 2026-05-14, última versión = 0.1.9). Alternativas evaluadas:
# - fastapi-limiter: requiere Redis como backend, no es drop-in.
# - Mantener slowapi 0.1.9 con shim: solución actual.
# Re-evaluar en cada release de slowapi o cuando se incorpore Redis al stack.
if sys.version_info >= (3, 14):
    asyncio.iscoroutinefunction = inspect.iscoroutinefunction  # type: ignore[misc]

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.middleware.rate_limit import limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s v%s arrancando", settings.APP_NAME, settings.APP_VERSION)
    # Fail-closed: hasta validar la licencia, el estado por defecto es inválido
    # (si algún paso del lifespan falla antes de validar, el middleware bloquea).
    app.state.license_valid = False
    app.state.license_plan = ""
    # ALB.4 — el esquema lo aplica Alembic desde `desktop/python-manager.js:runMigrations()`
    # antes de levantar el backend (ALB.5). El runtime ya NO emite DDL — toda
    # evolución de esquema vive en `backend/app/db/migrations/versions/`.
    # Recovery: tasks/executions zombi de reinicios previos.
    # Debe ejecutarse ANTES del scheduler para que no se intente reanudar
    # workflows huérfanos o ejecuciones colgadas.
    from app.services.workflow.recovery import recover_stale_executions

    try:
        await recover_stale_executions()
    except Exception:
        # Un fallo del recovery (p. ej. BD recién limpiada/sin migrar) NO debe
        # romper el arranque ni dejar el lifespan a medias (antes tumbaba el
        # backend y el frontend se quedaba sin respuesta → modal de licencia colgado).
        logger.exception("[STARTUP] recover_stale_executions falló (no bloquea el arranque)")

    # Licencia: estado inicial INSTANTÁNEO desde la caché local (sin red, no cuelga
    # el arranque ~60s en cold start). La validación real contra el servidor —que
    # tolera el cold start de Render— corre en background y refresca app.state.
    from app.core.license import cached_license_state, refresh_app_license_state

    init = cached_license_state()
    app.state.license_valid = init.valid
    app.state.license_plan = init.plan
    if init.valid:
        logger.info("[LICENSE] Estado inicial desde caché · plan=%s", init.plan)
    else:
        logger.info("[LICENSE] Sin licencia válida en caché (%s) — revalidando en background", init.reason)
    from app.core.background import spawn

    spawn(refresh_app_license_state(app), name="license.refresh")
    # Restaurar el consumo LLM persistido para que el dashboard sobreviva al reinicio.
    from app.services import llm_usage_tracker

    await llm_usage_tracker.load_from_db()
    # Arrancar scheduler
    from app.services.scheduler import scheduler, start_scheduler, stop_scheduler

    await start_scheduler()

    # L5 — revalidación periódica de licencia (cada 24 h) para que sesiones
    # largas no queden con un estado obsoleto. Captura `app` para refrescar
    # `app.state.license_valid` desde el job.
    import functools as _functools

    from apscheduler.triggers.interval import IntervalTrigger as _IntervalTrigger

    from app.core.license import refresh_app_license_state

    scheduler.add_job(
        _functools.partial(refresh_app_license_state, app),
        _IntervalTrigger(hours=24),
        id="revalidate_license",
        replace_existing=True,
        max_instances=1,
    )
    # Relay WebSocket ↔ Redis (sólo cuando REDIS_URL está configurado)
    from app.services.ws_relay import start_ws_relay, stop_ws_relay

    await start_ws_relay()
    yield
    # Parar scheduler, relay y tareas en vuelo
    await stop_ws_relay()
    await llm_usage_tracker.persist_to_db()
    await stop_scheduler()
    from app.services.workflow.task_runner import task_runner

    await task_runner.shutdown()
    logger.info("Cerrando aplicación")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SaaS de automatización administrativa multiagente para PYMEs",
    # En producción (DEBUG=False) ocultamos docs/redoc Y el esquema OpenAPI: con
    # acceso remoto el backend queda expuesto a internet y no debe revelar su
    # superficie de API. El túnel además solo enruta /api/v1 y /ws (ver
    # docs/remote-access-cloudflare.md), pero esto es defensa en profundidad.
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# CORS — acepta peticiones de los orígenes configurados en FRONTEND_URL (separados por coma)
_cors_origins = [u.strip() for u in settings.FRONTEND_URL.split(",") if u.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

from app.middleware.license_check import LicenseCheckMiddleware
from app.middleware.request_logger import RequestLoggerMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggerMiddleware)
app.add_middleware(LicenseCheckMiddleware)

from app.api.ws.notifications import router as ws_router

app.include_router(api_router)
app.include_router(ws_router)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    try:
        request_id = request.state.request_id
    except (AttributeError, TypeError):
        request_id = None
    logger.warning(
        "AppException %s on %s %s: %s",
        exc.error_type,
        request.method,
        request.url.path,
        exc.detail,
    )
    origin = request.headers.get("origin", "")
    cors_headers = {}
    if origin and origin in _cors_origins:
        cors_headers = {
            "access-control-allow-origin": origin,
            "access-control-allow-credentials": "true",
        }
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "type": exc.error_type,
            "request_id": request_id,
        },
        headers=cors_headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    try:
        request_id = request.state.request_id
    except (AttributeError, TypeError):
        request_id = None
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    # Include CORS headers so the browser can read the error response.
    # Without them, cross-origin requests see "Failed to fetch" instead of the real error.
    origin = request.headers.get("origin", "")
    cors_headers = {}
    if origin and origin in _cors_origins:
        cors_headers = {
            "access-control-allow-origin": origin,
            "access-control-allow-credentials": "true",
        }
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"{type(exc).__name__}: {exc}" if settings.DEBUG else "Error interno del servidor.",
            "type": "internal_error",
            "request_id": request_id,
        },
        headers=cors_headers,
    )


def _safe_import(module_name: str) -> bool:
    """Check if a module is importable without side effects."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


_app_start_time = __import__("time").monotonic()


@app.get("/metrics", tags=["system"])
async def metrics_endpoint():
    """Expose Prometheus metrics in text format."""
    from app.core.observability import get_metrics_registry

    registry = get_metrics_registry()
    if registry is None:
        return JSONResponse(
            {"detail": "Prometheus metrics not available (prometheus_client not installed)"},
            status_code=501,
        )
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    from starlette.responses import Response as StarletteResponse

    return StarletteResponse(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/health", tags=["system"])
async def health_check():
    """Health check: verifica PostgreSQL y servicios en memoria."""
    import os
    import sys
    import time

    from app.services.workflow.task_runner import task_runner

    health = {
        "status": "ok",
        "version": settings.APP_VERSION,
        "python_version": sys.version,
        "app_version": settings.APP_VERSION,
        "uptime_seconds": round(time.monotonic() - _app_start_time, 1),
        "memory_mb": round(__import__("psutil").Process(os.getpid()).memory_info().rss / 1024 / 1024, 1)
        if _safe_import("psutil")
        else None,
        "checks": {},
    }

    # ── PostgreSQL ────────────────────────────────────────────────────────
    try:
        from sqlalchemy import text

        from app.db.base import AsyncSessionLocal

        t0 = time.perf_counter()
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        health["checks"]["postgres"] = {"status": "up", "latency_ms": latency_ms}
    except Exception as e:
        health["checks"]["postgres"] = {"status": "down", "error": str(e)[:200]}
        health["status"] = "degraded"

    # ── Task Runner ───────────────────────────────────────────────────────
    health["checks"]["task_runner"] = {
        "status": "up",
        "active_tasks": task_runner.active_count,
    }

    # ── Redis / Scheduler / Backup ────────────────────────────────────────
    from app.services.health import check_last_backup, check_redis, check_scheduler

    health["checks"]["redis"] = await check_redis()
    health["checks"]["scheduler"] = check_scheduler()
    health["checks"]["last_backup"] = check_last_backup()

    # Si Redis está configurado y caído, marca degraded.
    if health["checks"]["redis"].get("status") == "down":
        health["status"] = "degraded"

    status_code = 200 if health["status"] == "ok" else 503
    return JSONResponse(health, status_code=status_code)


@app.get("/ready", tags=["system"])
async def readiness_check():
    """Readiness probe: returns 200 only if DB is reachable."""
    import time

    try:
        from sqlalchemy import text

        from app.db.base import AsyncSessionLocal

        t0 = time.perf_counter()
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        return JSONResponse({"ready": True, "db_latency_ms": latency_ms})
    except Exception as e:
        return JSONResponse(
            {"ready": False, "error": str(e)[:200]},
            status_code=503,
        )


@app.post("/lifecycle/shutdown", tags=["system"])
async def lifecycle_shutdown(request: Request):
    """Apagado grácil solicitado por el contenedor Electron antes del force-kill.

    Electron mata el proceso Python con `taskkill /F`, por lo que el lifespan de
    uvicorn (stop_scheduler + task_runner.shutdown) nunca corre. Este endpoint
    permite que el escritorio drene el scheduler y las tasks en vuelo antes de
    forzar el kill, dejando un estado limpio.

    Solo accesible desde loopback (la propia app); nunca desde la LAN aunque el
    backend escuche en ella (modo red local).
    """
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost"):
        return JSONResponse({"detail": "Forbidden"}, status_code=403)

    logger.info("[LIFECYCLE] Apagado grácil solicitado por %s", client_host)
    from app.services import llm_usage_tracker
    from app.services.scheduler import stop_scheduler
    from app.services.workflow.task_runner import task_runner

    try:
        await llm_usage_tracker.persist_to_db()
    except Exception as e:
        logger.warning("[LIFECYCLE] persist_to_db falló: %s", e)
    try:
        await stop_scheduler()
    except Exception as e:
        logger.warning("[LIFECYCLE] stop_scheduler falló: %s", e)
    try:
        await task_runner.shutdown()
    except Exception as e:
        logger.warning("[LIFECYCLE] task_runner.shutdown falló: %s", e)
    return {"status": "shutting_down"}


@app.get("/", tags=["system"])
async def root():
    return {"message": f"{settings.APP_NAME} API", "docs": "/docs"}
