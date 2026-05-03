"""Tests del módulo de backup automático.

Cubre:
- Parseo de DATABASE_URL en componentes pg_dump.
- Rotación: borra dumps con mtime > retention_days, deja los nuevos.
- run_backup_job respeta BACKUP_ENABLED=false.
- create_backup llama pg_dump con flags correctos y limpia el archivo
  si el subprocess falla.
"""

import os
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import backup as backup_module


def test_parse_db_url_postgresql_asyncpg_format():
    parsed = backup_module._parse_db_url(
        "postgresql+asyncpg://pyme_user:s3cret@localhost:5433/pyme_db"
    )
    assert parsed == {
        "host": "localhost",
        "port": 5433,
        "dbname": "pyme_db",
        "user": "pyme_user",
        "password": "s3cret",
    }


def test_parse_db_url_plain_postgresql_format():
    parsed = backup_module._parse_db_url(
        "postgresql://u:p@db.example.com:5432/mydb"
    )
    assert parsed["host"] == "db.example.com"
    assert parsed["port"] == 5432
    assert parsed["dbname"] == "mydb"


def test_parse_db_url_falls_back_to_defaults():
    parsed = backup_module._parse_db_url("postgresql:///mydb")
    assert parsed["host"] == "localhost"
    assert parsed["port"] == 5432
    assert parsed["user"] == ""


def test_rotate_backups_deletes_old_dumps(tmp_path: Path):
    old = tmp_path / "pyme_db_old.dump"
    new = tmp_path / "pyme_db_new.dump"
    old.write_bytes(b"x")
    new.write_bytes(b"y")

    # mtime 30 días atrás para old, ahora para new.
    old_ts = (time.time() - timedelta(days=30).total_seconds())
    os.utime(old, (old_ts, old_ts))

    deleted = backup_module.rotate_backups(backup_dir=tmp_path, retention_days=7)
    assert deleted == 1
    assert not old.exists()
    assert new.exists()


def test_rotate_backups_skips_non_dump_files(tmp_path: Path):
    """No tocar archivos que no son .dump (logs, otros)."""
    note = tmp_path / "README.txt"
    note.write_bytes(b"keep me")
    old_ts = time.time() - timedelta(days=30).total_seconds()
    os.utime(note, (old_ts, old_ts))

    backup_module.rotate_backups(backup_dir=tmp_path, retention_days=7)
    assert note.exists()


def test_rotate_backups_returns_zero_on_missing_dir(tmp_path: Path):
    missing = tmp_path / "no-such-dir"
    assert backup_module.rotate_backups(backup_dir=missing, retention_days=7) == 0


async def test_run_backup_job_skips_when_disabled(monkeypatch):
    monkeypatch.setattr(backup_module.settings, "BACKUP_ENABLED", False)
    result = await backup_module.run_backup_job()
    assert result == {"created": None, "rotated": 0, "status": "disabled"}


async def test_create_backup_returns_none_when_pg_dump_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module, "_find_pg_dump", lambda: None)
    result = await backup_module.create_backup(backup_dir=tmp_path)
    assert result is None


async def test_create_backup_invokes_pg_dump_with_correct_flags(monkeypatch, tmp_path):
    """Verifica que pg_dump recibe --format=custom, host/port/db correctos
    y que PGPASSWORD pasa por env (no por argv)."""
    monkeypatch.setattr(
        backup_module.settings,
        "DATABASE_URL",
        "postgresql+asyncpg://u:p@h:9999/d",
    )
    fake_pg_dump = tmp_path / "pg_dump.exe"
    fake_pg_dump.write_bytes(b"")
    monkeypatch.setattr(backup_module, "_find_pg_dump", lambda: fake_pg_dump)

    captured = {}

    async def fake_create_subprocess_exec(*args, env=None, **kwargs):
        captured["args"] = args
        captured["env"] = env
        # Simula que pg_dump escribió el archivo de salida exitosamente.
        out_path_str = args[args.index("--file") + 1]
        Path(out_path_str).write_bytes(b"fake-dump-content")
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate = AsyncMock(return_value=(b"", b""))
        return proc

    monkeypatch.setattr(
        backup_module.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    # Crea el archivo "manualmente" para simular el pg_dump exitoso.
    out = await backup_module.create_backup(backup_dir=tmp_path)
    # El proceso fake no escribe el archivo; esperamos que el código intente
    # abrir el .stat y eso fallará. Lo creamos antes de reflejar la realidad.
    # Simplificamos: el test asegura que los flags fueron correctos.

    args = captured["args"]
    assert "--format=custom" in args
    assert "--host" in args and "h" in args
    assert "--port" in args and "9999" in args
    assert "--dbname" in args and "d" in args
    assert "--username" in args and "u" in args
    # Password va por env, no por argv.
    assert "p" not in [a for a in args if a in ("--password", "p")]
    assert captured["env"]["PGPASSWORD"] == "p"


# ── Tests de los API helpers (list/get_path/delete + path traversal) ────────


def test_list_backups_returns_sorted_desc(monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module.settings, "BACKUP_DIR", str(tmp_path))
    a = tmp_path / "a.dump"
    b = tmp_path / "b.dump"
    a.write_bytes(b"x" * 100)
    b.write_bytes(b"x" * 200)
    # b más reciente que a.
    old = time.time() - 3600
    os.utime(a, (old, old))

    items = backup_module.list_backups()
    assert [i["filename"] for i in items] == ["b.dump", "a.dump"]
    assert items[0]["size_mb"] >= 0
    assert items[0]["age_hours"] < 1
    assert items[1]["age_hours"] >= 1


def test_list_backups_returns_empty_when_dir_missing(monkeypatch, tmp_path):
    missing = tmp_path / "no-such-dir"
    monkeypatch.setattr(backup_module.settings, "BACKUP_DIR", str(missing))
    assert backup_module.list_backups() == []


def test_resolve_safe_rejects_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module.settings, "BACKUP_DIR", str(tmp_path))
    for evil in [
        "../../../etc/passwd.dump",
        "..\\..\\windows\\system32.dump",
        "subdir/x.dump",
        "/absolute/path.dump",
        "..dump",
        "",
    ]:
        with pytest.raises(ValueError):
            backup_module._resolve_safe(evil)


def test_resolve_safe_rejects_non_dump_extension(monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module.settings, "BACKUP_DIR", str(tmp_path))
    with pytest.raises(ValueError, match=".dump"):
        backup_module._resolve_safe("backup.sql")


def test_resolve_safe_accepts_valid_filename(monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module.settings, "BACKUP_DIR", str(tmp_path))
    resolved = backup_module._resolve_safe("pyme_db_20260503_040000.dump")
    assert resolved.parent == tmp_path.resolve()


def test_get_backup_path_raises_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module.settings, "BACKUP_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        backup_module.get_backup_path("inexistente.dump")


def test_delete_backup_removes_file(monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module.settings, "BACKUP_DIR", str(tmp_path))
    target = tmp_path / "to_delete.dump"
    target.write_bytes(b"x")
    assert backup_module.delete_backup("to_delete.dump") is True
    assert not target.exists()


def test_delete_backup_returns_false_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module.settings, "BACKUP_DIR", str(tmp_path))
    assert backup_module.delete_backup("no_existe.dump") is False


def test_delete_backup_blocks_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module.settings, "BACKUP_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        backup_module.delete_backup("../../etc/passwd.dump")


async def test_create_backup_cleans_output_on_failure(monkeypatch, tmp_path):
    fake_pg_dump = tmp_path / "pg_dump.exe"
    fake_pg_dump.write_bytes(b"")
    monkeypatch.setattr(backup_module, "_find_pg_dump", lambda: fake_pg_dump)
    monkeypatch.setattr(
        backup_module.settings,
        "DATABASE_URL",
        "postgresql+asyncpg://u:p@h:5433/d",
    )

    async def fake_create_subprocess_exec(*args, env=None, **kwargs):
        # Simula que pg_dump creó el archivo a medias antes de fallar.
        # Buscamos el path del --file en argv.
        out_path_str = args[args.index("--file") + 1]
        Path(out_path_str).write_bytes(b"partial")
        proc = MagicMock()
        proc.returncode = 1
        proc.communicate = AsyncMock(return_value=(b"", b"connection failed"))
        return proc

    monkeypatch.setattr(
        backup_module.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    result = await backup_module.create_backup(backup_dir=tmp_path)
    assert result is None
    # El archivo parcial debe haberse limpiado.
    assert list(tmp_path.glob("*.dump")) == []
