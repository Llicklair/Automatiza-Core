"""
Guard de idempotencia en memoria.

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

Al ser single-process, un dict en memoria es suficiente.
"""
import json
import time
import threading
from datetime import datetime, UTC

_PREFIX = "idempotency"
_DEFAULT_TTL = 86_400  # 24 horas en segundos

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
    """Guard asíncrono de idempotencia en memoria."""

    def __init__(self, ttl: int = _DEFAULT_TTL):
        self.ttl = ttl

    async def already_executed(self, operation: str, entity_id: str) -> bool:
        _evict_expired()
        key = _make_key(operation, entity_id)
        with _lock:
            return key in _store

    async def mark_executed(
        self,
        operation: str,
        entity_id: str,
        result_summary: dict | None = None,
    ) -> None:
        key = _make_key(operation, entity_id)
        payload = json.dumps({
            "executed_at": datetime.now(UTC).isoformat(),
            "operation": operation,
            "entity_id": entity_id,
            "result": result_summary or {},
        })
        with _lock:
            _store[key] = (payload, time.time() + self.ttl)

    async def release(self, operation: str, entity_id: str) -> None:
        key = _make_key(operation, entity_id)
        with _lock:
            _store.pop(key, None)

    async def get_execution_info(self, operation: str, entity_id: str) -> dict | None:
        _evict_expired()
        key = _make_key(operation, entity_id)
        with _lock:
            entry = _store.get(key)
            if entry:
                return json.loads(entry[0])
            return None
