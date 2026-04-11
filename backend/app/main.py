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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s v%s arrancando", settings.APP_NAME, settings.APP_VERSION)
    # Arrancar scheduler
    from app.services.scheduler import start_scheduler, stop_scheduler
    await start_scheduler()
    yield
    # Parar scheduler y tareas en vuelo
    await stop_scheduler()
    from app.services.task_runner import task_runner
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
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — acepta peticiones de los orígenes configurados en FRONTEND_URL (separados por coma)
_cors_origins = [u.strip() for u in settings.FRONTEND_URL.split(",") if u.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """Pure-ASGI middleware — adds security headers without buffering the response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("X-Content-Type-Options", "nosniff")
                headers.append("X-Frame-Options", "DENY")
                headers.append("X-XSS-Protection", "1; mode=block")
                headers.append("Referrer-Policy", "strict-origin-when-cross-origin")
                if settings.ENVIRONMENT == "production":
                    headers.append("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
            await send(message)

        await self.app(scope, receive, send_with_headers)


app.add_middleware(SecurityHeadersMiddleware)

from app.middleware.request_logger import RequestLoggerMiddleware

app.add_middleware(RequestLoggerMiddleware)

from app.api.ws.notifications import router as ws_router

app.include_router(api_router)
app.include_router(ws_router)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        "AppException %s on %s %s: %s",
        exc.error_type, request.method, request.url.path, exc.detail,
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
    request_id = getattr(request.state, "request_id", None)
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

    from app.services.task_runner import task_runner

    health = {
        "status": "ok",
        "version": settings.APP_VERSION,
        "python_version": sys.version,
        "app_version": settings.APP_VERSION,
        "uptime_seconds": round(time.monotonic() - _app_start_time, 1),
        "memory_mb": round(__import__("psutil").Process(os.getpid()).memory_info().rss / 1024 / 1024, 1) if _safe_import("psutil") else None,
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
