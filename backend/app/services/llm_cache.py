"""
Caché de respuestas LLM en Redis.

Estrategia:
    - Clave = hash SHA-256 de (tenant_id + intent + provider)
    - TTL configurable (default 1h para respuestas operativas)
    - Solo cachea respuestas exitosas (no errores)
    - Invalidación automática por TTL

Uso:
    cache = LLMCache()
    cached = await cache.get(tenant_id, intent)
    if cached:
        return cached
    response = await llm.ainvoke(...)
    await cache.set(tenant_id, intent, response)
"""

import hashlib
import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_PREFIX = "llm_cache"
_DEFAULT_TTL = 3600  # 1 hora


def _make_key(tenant_id: str, intent: str, provider: str = "") -> str:
    """Genera clave Redis como hash SHA-256 de tenant+intent+provider."""
    raw = f"{tenant_id}:{intent.strip().lower()}:{provider}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"{_PREFIX}:{digest}"


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


class LLMCache:
    """Caché asíncrono de respuestas LLM en Redis."""

    def __init__(self, ttl: int = _DEFAULT_TTL):
        self.ttl = ttl

    async def get(
        self,
        tenant_id: str,
        intent: str,
        provider: str = "",
    ) -> Optional[str]:
        """Devuelve la respuesta cacheada o None."""
        try:
            r = await _get_redis()
            try:
                key = _make_key(tenant_id, intent, provider)
                value = await r.get(key)
                if value:
                    logger.debug("LLM cache HIT: %s", key[:32])
                    data = json.loads(value)
                    return data.get("response")
                return None
            finally:
                await r.aclose()
        except Exception as e:
            logger.warning("LLM cache GET error (degradando sin caché): %s", e)
            return None

    async def set(
        self,
        tenant_id: str,
        intent: str,
        response: str,
        provider: str = "",
        metadata: Optional[dict] = None,
        ttl_override: Optional[int] = None,
    ) -> None:
        """Almacena respuesta en caché con TTL."""
        try:
            r = await _get_redis()
            try:
                key = _make_key(tenant_id, intent, provider)
                ttl = ttl_override or self.ttl
                payload = json.dumps({
                    "response": response,
                    "provider": provider,
                    "tenant_id": tenant_id,
                    "metadata": metadata or {},
                })
                await r.setex(key, ttl, payload)
                logger.debug("LLM cache SET: %s (TTL=%ds)", key[:32], self.ttl)
            finally:
                await r.aclose()
        except Exception as e:
            logger.warning("LLM cache SET error (continuando sin caché): %s", e)

    async def invalidate(
        self,
        tenant_id: str,
        intent: str,
        provider: str = "",
    ) -> None:
        """Elimina una entrada de caché manualmente."""
        try:
            r = await _get_redis()
            try:
                key = _make_key(tenant_id, intent, provider)
                await r.delete(key)
            finally:
                await r.aclose()
        except Exception as e:
            logger.warning("LLM cache INVALIDATE error: %s", e)

    async def flush_tenant(self, tenant_id: str) -> int:
        """Elimina TODAS las entradas de caché de un tenant (usa SCAN)."""
        count = 0
        try:
            r = await _get_redis()
            try:
                async for key in r.scan_iter(f"{_PREFIX}:*"):
                    # Comprobamos leyendo el payload (no podemos deducir tenant del hash)
                    raw = await r.get(key)
                    if raw:
                        try:
                            data = json.loads(raw)
                            if data.get("tenant_id") == tenant_id:
                                await r.delete(key)
                                count += 1
                        except json.JSONDecodeError:
                            pass
                return count
            finally:
                await r.aclose()
        except Exception as e:
            logger.warning("LLM cache FLUSH error: %s", e)
            return count


# Singleton para uso global
llm_cache = LLMCache()
