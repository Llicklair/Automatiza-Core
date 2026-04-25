"""Aplicación principal FastAPI."""

import asyncio
import inspect
import logging
import sys
from contextlib import asynccontextmanager

# Python 3.14+ depreca asyncio.iscoroutinefunction; slowapi 0.1.x aún la usa.
# Debe ir antes de cualquier import de slowapi.
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


async def _ensure_schema() -> None:
    """Aplica columnas nuevas con IF NOT EXISTS — idempotente, sin dependencia de rutas."""
    from sqlalchemy import text
    from app.db.base import engine

    statements = [
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS document_id UUID REFERENCES tenant_documents(id)",
        "ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS invoice_id UUID REFERENCES invoices(id)",
        "ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS payroll_id UUID REFERENCES payrolls(id)",
        "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS journal_entry_id UUID REFERENCES journal_entries(id)",
        "CREATE INDEX IF NOT EXISTS ix_journal_entries_invoice_id ON journal_entries(invoice_id)",
        "CREATE INDEX IF NOT EXISTS ix_journal_entries_payroll_id ON journal_entries(payroll_id)",
        """CREATE TABLE IF NOT EXISTS generated_uis (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            prompt TEXT NOT NULL,
            content_html TEXT NOT NULL,
            is_pinned BOOLEAN NOT NULL DEFAULT TRUE,
            metadata_json JSON,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_generated_uis_tenant_id ON generated_uis(tenant_id)",
    ]
    try:
        async with engine.begin() as conn:
            for stmt in statements:
                await conn.execute(text(stmt))
        logger.info("[SCHEMA] Columnas cross-domain verificadas/creadas OK")
    except Exception as e:
        logger.warning("[SCHEMA] Error aplicando schema: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s v%s arrancando", settings.APP_NAME, settings.APP_VERSION)
    # Aplicar columnas nuevas (idempotente)
    await _ensure_schema()
    # Arrancar scheduler
    from app.services.scheduler import start_scheduler, stop_scheduler

    await start_scheduler()
    yield
    # Parar scheduler y tareas en vuelo
    await stop_scheduler()
    from app.services.workflow.task_runner import task_runner

    await task_runner.shutdown()
    logger.info("Cerrando aplicación")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SaaS de automatización administrativa multiagente para PYMEs",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
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

from app.middleware.request_logger import RequestLoggerMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(RequestLoggerMiddleware)

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
    logger.error(
        "Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True
    )
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
            "detail": f"{type(exc).__name__}: {exc}"
            if settings.DEBUG
            else "Error interno del servidor.",
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
        "memory_mb": round(
            __import__("psutil").Process(os.getpid()).memory_info().rss / 1024 / 1024, 1
        )
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


@app.get("/", tags=["system"])
async def root():
    return {"message": f"{settings.APP_NAME} API", "docs": "/docs"}
