"""
Guard de idempotencia usando Redis.

Patrón:
    key  = "<operacion>:<id_unico>"   ej: "run_orchestrator:abc-123"
    TTL  = 24 horas por defecto

Uso:
    guard = IdempotencyGuard()
    if await guard.already_executed("run_orchestrator", task_id):
        return  # skip — ya se ejecutó
    try:
        ... lógica ...
        await guard.mark_executed("run_orchestrator", task_id)
    except Exception:
        await guard.release("run_orchestrator", task_id)  # permitir reintento
        raise

Las claves se almacenan en Redis con TTL para no acumular entradas indefinidamente.
"""
import json
from datetime import datetime, UTC

import redis.asyncio as aioredis

from app.core.config import settings


_PREFIX = "idempotency"
_DEFAULT_TTL = 86_400  # 24 horas en segundos


def _make_key(operation: str, entity_id: str) -> str:
    return f"{_PREFIX}:{operation}:{entity_id}"


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)


class IdempotencyGuard:
    """
    Guard asíncrono de idempotencia basado en Redis.
    Thread-safe para múltiples workers Celery.
    """

    def __init__(self, ttl: int = _DEFAULT_TTL):
        self.ttl = ttl

    async def already_executed(self, operation: str, entity_id: str) -> bool:
        """
        Devuelve True si la operación ya fue ejecutada para ese entity_id.
        """
        redis = await _get_redis()
        try:
            key = _make_key(operation, entity_id)
            value = await redis.get(key)
            return value is not None
        finally:
            await redis.aclose()

    async def mark_executed(
        self,
        operation: str,
        entity_id: str,
        result_summary: dict | None = None,
    ) -> None:
        """
        Marca la operación como ejecutada en Redis con TTL.
        Almacena opcionalmente un resumen del resultado para debugging.
        """
        redis = await _get_redis()
        try:
            key = _make_key(operation, entity_id)
            payload = json.dumps({
                "executed_at": datetime.now(UTC).isoformat(),
                "operation": operation,
                "entity_id": entity_id,
                "result": result_summary or {},
            })
            await redis.setex(key, self.ttl, payload)
        finally:
            await redis.aclose()

    async def release(self, operation: str, entity_id: str) -> None:
        """
        Elimina la clave de idempotencia para permitir un reintento limpio.
        Llamar en bloques except cuando el error es recuperable.
        """
        redis = await _get_redis()
        try:
            key = _make_key(operation, entity_id)
            await redis.delete(key)
        finally:
            await redis.aclose()

    async def get_execution_info(self, operation: str, entity_id: str) -> dict | None:
        """
        Devuelve la info de la ejecución guardada o None si no existe.
        Útil para debugging y auditoría.
        """
        redis = await _get_redis()
        try:
            key = _make_key(operation, entity_id)
            value = await redis.get(key)
            if value:
                return json.loads(value)
            return None
        finally:
            await redis.aclose()


# ─── Versión síncrona para usar dentro de tasks Celery (que son sync) ─────────

import redis as sync_redis


def _get_sync_redis() -> sync_redis.Redis:
    return sync_redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)


class SyncIdempotencyGuard:
    """
    Guard síncrono de idempotencia para usar dentro de tasks Celery (@celery_app.task).
    Misma lógica que IdempotencyGuard pero sin async/await.
    """

    def __init__(self, ttl: int = _DEFAULT_TTL):
        self.ttl = ttl

    def already_executed(self, operation: str, entity_id: str) -> bool:
        r = _get_sync_redis()
        try:
            return r.get(_make_key(operation, entity_id)) is not None
        finally:
            r.close()

    def mark_executed(
        self,
        operation: str,
        entity_id: str,
        result_summary: dict | None = None,
    ) -> None:
        r = _get_sync_redis()
        try:
            key = _make_key(operation, entity_id)
            payload = json.dumps({
                "executed_at": datetime.now(UTC).isoformat(),
                "operation": operation,
                "entity_id": entity_id,
                "result": result_summary or {},
            })
            r.setex(key, self.ttl, payload)
        finally:
            r.close()

    def release(self, operation: str, entity_id: str) -> None:
        r = _get_sync_redis()
        try:
            r.delete(_make_key(operation, entity_id))
        finally:
            r.close()
