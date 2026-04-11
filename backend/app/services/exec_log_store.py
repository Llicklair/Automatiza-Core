"""
Almacén en memoria para logs de ejecución de tareas.
"""

import threading
import time

_LOG_TTL = 7200  # 2 horas

_logs: dict[str, list[str]] = {}
_expiry: dict[str, float] = {}
_lock = threading.Lock()


def push(task_id: str, line: str) -> None:
    """Añade una línea de log para una tarea."""
    with _lock:
        if task_id not in _logs:
            _logs[task_id] = []
        _logs[task_id].append(line)
        _expiry[task_id] = time.time() + _LOG_TTL


def get_all(task_id: str) -> list[str]:
    """Devuelve todas las líneas de log de una tarea."""
    _evict_expired()
    with _lock:
        return list(_logs.get(task_id, []))


def clear(task_id: str) -> None:
    with _lock:
        _logs.pop(task_id, None)
        _expiry.pop(task_id, None)


def _evict_expired() -> None:
    """Limpieza lazy de logs expirados."""
    now = time.time()
    with _lock:
        expired = [k for k, exp in _expiry.items() if exp < now]
        for k in expired:
            _logs.pop(k, None)
            _expiry.pop(k, None)
