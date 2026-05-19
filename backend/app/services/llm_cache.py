from __future__ import annotations

"""
Caché de respuestas LLM en memoria.

Estrategia:
    - Clave = hash SHA-256 de (tenant_id + intent + provider)
    - TTL configurable (default 1h para respuestas operativas)
    - Solo cachea respuestas exitosas (no errores)
    - Máximo 1000 entradas (evita memory leak)
"""

import hashlib
import json
import logging
import threading
import time

logger = logging.getLogger(__name__)

_PREFIX = "llm_cache"
_DEFAULT_TTL = 3600  # 1 hora
_MAX_ENTRIES = 1000

_cache: dict[str, tuple[str, float]] = {}  # key -> (payload_json, expiry)
_lock = threading.Lock()


def _make_key(tenant_id: str, intent: str, provider: str = "") -> str:
    raw = f"{tenant_id}:{intent.strip().lower()}:{provider}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"{_PREFIX}:{digest}"


def _evict_expired() -> None:
    now = time.time()
    with _lock:
        expired = [k for k, (_, exp) in _cache.items() if exp < now]
        for k in expired:
            del _cache[k]


def _evict_oldest() -> None:
    """Elimina las entradas más antiguas si se supera el límite."""
    with _lock:
        if len(_cache) <= _MAX_ENTRIES:
            return
        sorted_keys = sorted(_cache, key=lambda k: _cache[k][1])
        to_remove = len(_cache) - _MAX_ENTRIES
        for k in sorted_keys[:to_remove]:
            del _cache[k]


class LLMCache:
    """Caché asíncrono de respuestas LLM en memoria."""

    def __init__(self, ttl: int = _DEFAULT_TTL):
        self.ttl = ttl

    async def get(
        self,
        tenant_id: str,
        intent: str,
        provider: str = "",
    ) -> str | None:
        _evict_expired()
        key = _make_key(tenant_id, intent, provider)
        with _lock:
            entry = _cache.get(key)
            if entry:
                logger.debug("LLM cache HIT: %s", key[:32])
                data = json.loads(entry[0])
                return data.get("response")
        return None

    async def set(
        self,
        tenant_id: str,
        intent: str,
        response: str,
        provider: str = "",
        metadata: dict | None = None,
        ttl_override: int | None = None,
    ) -> None:
        key = _make_key(tenant_id, intent, provider)
        ttl = ttl_override or self.ttl
        payload = json.dumps(
            {
                "response": response,
                "provider": provider,
                "tenant_id": tenant_id,
                # Guardamos el intent original normalizado para permitir
                # invalidación por prefijo ("classify:*", "plan:*", …) desde
                # flush_prefix. Sin esto la clave es un sha256 opaco y no se
                # puede filtrar por familia.
                "intent": intent,
                "metadata": metadata or {},
            }
        )
        with _lock:
            _cache[key] = (payload, time.time() + ttl)
        _evict_oldest()
        logger.debug("LLM cache SET: %s (TTL=%ds)", key[:32], ttl)

    async def invalidate(
        self,
        tenant_id: str,
        intent: str,
        provider: str = "",
    ) -> None:
        key = _make_key(tenant_id, intent, provider)
        with _lock:
            _cache.pop(key, None)

    async def flush_prefix(self, prefix: str, tenant_id: str | None = None) -> int:
        """Invalida todas las entradas cuyo `intent` original empiece por `prefix`.

        Útil para purgar familias enteras del cache (p.ej. ``classify:*`` tras
        cambiar las reglas de keywords, ``plan:*`` tras tocar el prompt del
        planner). Si `tenant_id` es None, purga across todos los tenants.

        Devuelve el número de entradas eliminadas.
        """
        count = 0
        _evict_expired()
        with _lock:
            keys_to_delete = []
            for key, (payload_json, _) in _cache.items():
                try:
                    data = json.loads(payload_json)
                except json.JSONDecodeError:
                    logger.warning("Skipping corrupted cache entry (invalid JSON), key=%s", key)
                    continue
                if tenant_id is not None and data.get("tenant_id") != tenant_id:
                    continue
                intent = data.get("intent") or ""
                if isinstance(intent, str) and intent.startswith(prefix):
                    keys_to_delete.append(key)
            for k in keys_to_delete:
                del _cache[k]
                count += 1
        return count

    async def flush_tenant(self, tenant_id: str) -> int:
        count = 0
        _evict_expired()
        with _lock:
            keys_to_delete = []
            for key, (payload_json, _) in _cache.items():
                try:
                    data = json.loads(payload_json)
                    if data.get("tenant_id") == tenant_id:
                        keys_to_delete.append(key)
                except json.JSONDecodeError:
                    logger.warning("Skipping corrupted cache entry (invalid JSON), key=%s", key)
            for k in keys_to_delete:
                del _cache[k]
                count += 1
        return count


# Singleton para uso global
llm_cache = LLMCache()
