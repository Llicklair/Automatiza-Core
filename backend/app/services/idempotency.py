"""
Guard de idempotencia persistente en DB (tabla `idempotency_keys`).

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

Antes vivía en un dict en memoria: un reinicio de la app dentro de la ventana
del cron podía re-ejecutar jobs no idempotentes (p.ej. emitir dos veces una
factura recurrente). Ahora las claves sobreviven
reinicios. Si la DB no está disponible se degrada al dict en memoria (mejor
una clave volátil que tumbar el scheduler).
"""

import json
import logging
import threading
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.db.models import IdempotencyKey

logger = logging.getLogger(__name__)

_PREFIX = "idempotency"
_DEFAULT_TTL = 86_400  # 24 horas en segundos

# Fallback en memoria si la DB falla (comportamiento legacy).
_store: dict[str, tuple[str, float]] = {}  # key -> (payload_json, expiry_timestamp)
_lock = threading.Lock()


def _make_key(operation: str, entity_id: str) -> str:
    return f"{_PREFIX}:{operation}:{entity_id}"


def _evict_expired() -> None:
    now = time.time()
    with _lock:
        expired = [k for k, (_, exp) in _store.items() if exp < now]
        for k in expired:
            del _store[k]


class IdempotencyGuard:
    """Guard asíncrono de idempotencia respaldado por DB."""

    def __init__(self, ttl: int = _DEFAULT_TTL):
        self.ttl = ttl

    async def already_executed(self, operation: str, entity_id: str) -> bool:
        info = await self.get_execution_info(operation, entity_id)
        return info is not None

    async def mark_executed(
        self,
        operation: str,
        entity_id: str,
        result_summary: dict | None = None,
    ) -> None:
        key = _make_key(operation, entity_id)
        payload = json.dumps(
            {
                "executed_at": datetime.now(UTC).isoformat(),
                "operation": operation,
                "entity_id": entity_id,
                "result": result_summary or {},
            }
        )
        expires_at = datetime.now(UTC) + timedelta(seconds=self.ttl)
        try:
            from app.db.base import AsyncSessionLocal  # noqa: PLC0415

            async with AsyncSessionLocal() as db:
                existing = await db.get(IdempotencyKey, key)
                if existing is not None:
                    existing.payload = payload
                    existing.expires_at = expires_at
                else:
                    db.add(IdempotencyKey(key=key, payload=payload, expires_at=expires_at))
                await db.commit()
        except Exception:
            logger.exception("[IDEMPOTENCY] DB no disponible; usando memoria para %s", key)
            with _lock:
                _store[key] = (payload, time.time() + self.ttl)

    async def release(self, operation: str, entity_id: str) -> None:
        key = _make_key(operation, entity_id)
        with _lock:
            _store.pop(key, None)
        try:
            from app.db.base import AsyncSessionLocal  # noqa: PLC0415

            async with AsyncSessionLocal() as db:
                await db.execute(delete(IdempotencyKey).where(IdempotencyKey.key == key))
                await db.commit()
        except Exception:
            logger.exception("[IDEMPOTENCY] Error liberando %s en DB", key)

    async def get_execution_info(self, operation: str, entity_id: str) -> dict | None:
        _evict_expired()
        key = _make_key(operation, entity_id)
        with _lock:
            entry = _store.get(key)
        if entry:
            return json.loads(entry[0])
        try:
            from app.db.base import AsyncSessionLocal  # noqa: PLC0415

            async with AsyncSessionLocal() as db:
                row = (
                    await db.execute(
                        select(IdempotencyKey).where(
                            IdempotencyKey.key == key,
                            IdempotencyKey.expires_at > datetime.now(UTC),
                        )
                    )
                ).scalar_one_or_none()
                if row is not None and row.payload:
                    return json.loads(row.payload)
        except Exception:
            logger.exception("[IDEMPOTENCY] DB no disponible consultando %s", key)
        return None


async def purge_expired_keys() -> int:
    """Borra claves expiradas de la tabla. Pensado para un job periódico."""
    from app.db.base import AsyncSessionLocal  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        result = await db.execute(delete(IdempotencyKey).where(IdempotencyKey.expires_at <= datetime.now(UTC)))
        await db.commit()
        return result.rowcount or 0
