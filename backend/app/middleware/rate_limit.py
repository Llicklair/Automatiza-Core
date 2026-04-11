"""Rate limiting middleware usando slowapi (Starlette compatible)."""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Respuesta estándar cuando se supera el límite de peticiones."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Demasiadas peticiones. Por favor espera antes de reintentar.",
            "retry_after": exc.retry_after if hasattr(exc, "retry_after") else 60,
        },
    )
