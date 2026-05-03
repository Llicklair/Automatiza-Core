"""Caché Redis async ligera con degradación silenciosa.

Si `settings.REDIS_URL` no está configurado, todas las operaciones son
no-op y el código de aplicación sigue funcionando sin caché. Esto es
crítico para el flujo single-tenant desktop donde Redis puede no estar
disponible (la app desktop solo levanta Redis si Celery está habilitado).

Uso típico:

    @cached_json(
        key=lambda tenant_id, period, **_: f"dashboard:v1:{tenant_id}:{period}",
        ttl_seconds=900,
    )
    async def get_dashboard(db, tenant_id, period, start, end) -> dict:
        ...

Convención de keys: `<dominio>:v<N>:<scope>:<params>`. Subir N invalida
todo el dominio cuando cambia el shape del payload (no hay que limpiar
Redis manualmente).
"""

from __future__ import annotations

import functools
import json
import logging
from typing import Any, Awaitable, Callable

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Any = None
_redis_init_attempted: bool = False


def _get_redis() -> Any | None:
    """Devuelve el cliente Redis async lazy. None si REDIS_URL no configurado
    o si la conexión falla (degradación silenciosa)."""
    global _redis_client, _redis_init_attempted

    if _redis_client is not None:
        return _redis_client
    if _redis_init_attempted:
        return None  # ya intentamos y fracasamos en este proceso

    _redis_init_attempted = True

    if not settings.REDIS_URL:
        return None

    try:
        from redis import asyncio as aioredis

        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        return _redis_client
    except Exception as exc:
        logger.warning("Cache: no se pudo inicializar Redis (%s). Caché desactivada.", exc)
        return None


async def cache_get(key: str) -> Any | None:
    """Devuelve el valor JSON-deserializado o None si no existe / Redis caído."""
    client = _get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except Exception as exc:
        logger.debug("Cache get falló para '%s': %s", key, exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int) -> bool:
    """Guarda el valor serializado a JSON. Silencioso si falla."""
    client = _get_redis()
    if client is None:
        return False
    try:
        # default=str serializa date/datetime como ISO 8601 — los endpoints
        # FastAPI los devuelven como string al cliente, mismo comportamiento.
        payload = json.dumps(value, default=str, ensure_ascii=False)
        await client.set(key, payload, ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.debug("Cache set falló para '%s': %s", key, exc)
        return False


async def cache_invalidate(key: str) -> bool:
    """Borra una key. No-op silencioso si Redis no disponible."""
    client = _get_redis()
    if client is None:
        return False
    try:
        await client.delete(key)
        return True
    except Exception:
        return False


def cached_json(
    key: Callable[..., str],
    ttl_seconds: int,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorador para funciones async que devuelven dict/list serializables.

    `key` es una función que recibe los mismos args/kwargs que la función
    decorada y devuelve la cache key. Permite componerla a partir de
    parámetros relevantes (tenant_id, period, etc.).
    """

    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = key(*args, **kwargs)
            cached = await cache_get(cache_key)
            if cached is not None:
                return cached
            result = await fn(*args, **kwargs)
            await cache_set(cache_key, result, ttl_seconds)
            return result

        return wrapper

    return decorator
