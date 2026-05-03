"""Tests de los health checks adicionales (redis, scheduler, last_backup)."""

import importlib.util
import os
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import health

_redis_available = importlib.util.find_spec("redis") is not None


async def test_check_redis_disabled_when_no_url(monkeypatch):
    monkeypatch.setattr(health.settings, "REDIS_URL", None)
    result = await health.check_redis()
    assert result == {"status": "disabled"}


@pytest.mark.skipif(not _redis_available, reason="redis-py no instalado en el venv")
async def test_check_redis_up_with_fake_client(monkeypatch):
    monkeypatch.setattr(health.settings, "REDIS_URL", "redis://localhost:6379/0")

    fake = MagicMock()
    fake.ping = AsyncMock(return_value=True)
    fake.aclose = AsyncMock()

    with patch("redis.asyncio.from_url", return_value=fake):
        result = await health.check_redis()

    assert result["status"] == "up"
    assert "latency_ms" in result
    fake.aclose.assert_awaited_once()


@pytest.mark.skipif(not _redis_available, reason="redis-py no instalado en el venv")
async def test_check_redis_down_when_ping_fails(monkeypatch):
    monkeypatch.setattr(health.settings, "REDIS_URL", "redis://localhost:6379/0")

    fake = MagicMock()
    fake.ping = AsyncMock(side_effect=ConnectionError("redis unreachable"))
    fake.aclose = AsyncMock()

    with patch("redis.asyncio.from_url", return_value=fake):
        result = await health.check_redis()

    assert result["status"] == "down"
    assert "redis unreachable" in result["error"]


def test_check_scheduler_reports_running_jobs():
    fake_job = MagicMock()
    fake_job.next_run_time = None
    fake_scheduler = MagicMock()
    fake_scheduler.running = True
    fake_scheduler.get_jobs.return_value = [fake_job, fake_job, fake_job]

    with patch("app.services.scheduler.scheduler", fake_scheduler):
        result = health.check_scheduler()

    assert result["status"] == "up"
    assert result["jobs"] == 3
    assert result["running"] is True


def test_check_scheduler_down_when_not_running():
    fake_scheduler = MagicMock()
    fake_scheduler.running = False

    with patch("app.services.scheduler.scheduler", fake_scheduler):
        result = health.check_scheduler()

    assert result["status"] == "down"
    assert result["running"] is False


def test_check_last_backup_disabled(monkeypatch):
    monkeypatch.setattr(health.settings, "BACKUP_ENABLED", False)
    result = health.check_last_backup()
    assert result == {"status": "disabled"}


def test_check_last_backup_never_when_dir_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(health.settings, "BACKUP_ENABLED", True)
    monkeypatch.setattr(health.settings, "BACKUP_DIR", str(tmp_path))
    result = health.check_last_backup()
    assert result["status"] == "never"
    assert result["path"] == str(tmp_path)


def test_check_last_backup_returns_metadata_of_latest(monkeypatch, tmp_path):
    monkeypatch.setattr(health.settings, "BACKUP_ENABLED", True)
    monkeypatch.setattr(health.settings, "BACKUP_DIR", str(tmp_path))

    old = tmp_path / "pyme_db_old.dump"
    new = tmp_path / "pyme_db_new.dump"
    old.write_bytes(b"x" * 1024)
    new.write_bytes(b"y" * 2048)

    # old: 24h atrás; new: ahora.
    old_ts = time.time() - 24 * 3600
    os.utime(old, (old_ts, old_ts))

    result = health.check_last_backup()
    assert result["status"] == "ok"
    assert result["file"] == "pyme_db_new.dump"
    assert result["age_hours"] < 1
    assert result["total_dumps"] == 2
    assert result["size_mb"] >= 0
