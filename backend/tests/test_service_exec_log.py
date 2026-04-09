"""Tests para app.services.exec_log_store — buffer en memoria con TTL."""
import time
from unittest.mock import patch

from app.services.exec_log_store import clear, get_all, push, _evict_expired, _logs, _expiry


class TestExecLogStore:
    def setup_method(self):
        """Limpiar estado global entre tests."""
        _logs.clear()
        _expiry.clear()

    def test_push_and_get(self):
        push("task-1", "Linea 1")
        push("task-1", "Linea 2")
        lines = get_all("task-1")
        assert lines == ["Linea 1", "Linea 2"]

    def test_get_nonexistent_task(self):
        assert get_all("no-existe") == []

    def test_clear(self):
        push("task-2", "log")
        clear("task-2")
        assert get_all("task-2") == []

    def test_clear_nonexistent_no_error(self):
        clear("no-existe")  # no debe lanzar

    def test_multiple_tasks_isolated(self):
        push("a", "log-a")
        push("b", "log-b")
        assert get_all("a") == ["log-a"]
        assert get_all("b") == ["log-b"]

    def test_ttl_eviction(self):
        push("old-task", "old log")
        # Forzar expiracion
        _expiry["old-task"] = time.time() - 1
        lines = get_all("old-task")
        assert lines == []

    def test_push_updates_expiry(self):
        push("task-3", "line 1")
        first_expiry = _expiry["task-3"]
        time.sleep(0.01)
        push("task-3", "line 2")
        assert _expiry["task-3"] > first_expiry
