"""Rate limiting middleware usando slowapi (Starlette compatible)."""

import warnings

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _client_ip(request: Request) -> str:
    """IP real del cliente para el rate limiting.

    En acceso remoto el backend se sirve tras un proxy inverso (Cloudflare
    Tunnel) que corre en la MISMA máquina: las peticiones llegan desde loopback
    y la IP real del visitante viaja en `CF-Connecting-IP` (o `X-Forwarded-For`).
    Sin esto, todos los empleados remotos compartirían una sola clave de límite
    (la del edge) y se bloquearían entre sí.

    Solo confiamos en esas cabeceras cuando el peer inmediato es loopback (el
    túnel local). Así un cliente directo en LAN/internet NO puede falsificarlas
    para evadir el límite. En acceso directo usamos la IP del socket.
    """
    peer = get_remote_address(request)
    if peer in _LOOPBACK:
        forwarded = request.headers.get("CF-Connecting-IP") or request.headers.get(
            "X-Forwarded-For"
        )
        if forwarded:
            return forwarded.split(",")[0].strip()
    return peer


# `config_filename=""` desactiva la lectura automática de slowapi de un `.env`
# del cwd: starlette lo abre con la codificación del SO (cp1252 en Windows) y
# crashea con `UnicodeDecodeError` ante un `.env` con bytes UTF-8 (rompía la
# colección de tests y es frágil en producción). No necesitamos esa config: el
# storage se fija aquí explícitamente y los RATELIMIT_* usan sus defaults.
# starlette avisa "Config file '' not found" por el env_file vacío: es esperado.
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="Config file.*not found", category=UserWarning)
    limiter = Limiter(key_func=_client_ip, storage_uri="memory://", config_filename="")


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Respuesta estándar cuando se supera el límite de peticiones."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Demasiadas peticiones. Por favor espera antes de reintentar.",
            "retry_after": exc.retry_after if hasattr(exc, "retry_after") else 60,
        },
    )
