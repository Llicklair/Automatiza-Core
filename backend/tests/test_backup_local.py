"""Tests para registro de backups locales (BAK.LOC + BAK.VF + BAK.UI)."""
from datetime import UTC, datetime, timedelta

import pytest
from app.db.models.backup import BackupRecord
from app.main import app
from app.services.backup_local import (
    BACKUP_STALE_THRESHOLD_DAYS,
    backup_status_for_banner,
    compute_file_sha256,
    get_last_backup,
    record_backup,
)
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
class TestRecordBackup:
    async def test_record_full_backup(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        rec = await record_backup(
            db,
            tenant_id=tenant.id,
            kind="full",
            destination_path="C:/Users/X/Documents/backup-2026-05-14.dump.enc",
            size_bytes=1024,
            sha256_hex="0" * 64,
            encryption_key_label="user_master",
            note="Backup automático",
        )
        await db.commit()
        assert rec.id is not None
        assert rec.kind == "full"
        assert rec.size_bytes == 1024

    async def test_record_verifactu_backup(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        rec = await record_backup(
            db,
            tenant_id=tenant.id,
            kind="verifactu",
            destination_path="C:/.../verifactu-2026-05-14.dump.enc",
            size_bytes=512,
            sha256_hex="f" * 64,
            encryption_key_label="verifactu_segregated",
        )
        await db.commit()
        assert rec.kind == "verifactu"
        assert rec.encryption_key_label == "verifactu_segregated"


@pytest.mark.asyncio
class TestGetLastBackup:
    async def test_devuelve_none_sin_backups(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        last = await get_last_backup(db, tenant_id=tenant.id)
        assert last is None

    async def test_devuelve_el_mas_reciente(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        # Insertar 3 backups con created_at distintos
        old = BackupRecord(
            tenant_id=tenant.id, kind="full", destination_path="/a",
            size_bytes=1, sha256_hex="a" * 64, encryption_key_label="x",
            created_at=datetime.now(UTC) - timedelta(days=10),
        )
        mid = BackupRecord(
            tenant_id=tenant.id, kind="full", destination_path="/b",
            size_bytes=2, sha256_hex="b" * 64, encryption_key_label="x",
            created_at=datetime.now(UTC) - timedelta(days=2),
        )
        new = BackupRecord(
            tenant_id=tenant.id, kind="full", destination_path="/c",
            size_bytes=3, sha256_hex="c" * 64, encryption_key_label="x",
            created_at=datetime.now(UTC),
        )
        db.add_all([old, mid, new])
        await db.commit()

        last = await get_last_backup(db, tenant_id=tenant.id, kind="full")
        assert last is not None
        assert last.destination_path == "/c"

    async def test_filtra_por_kind(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        await record_backup(
            db, tenant_id=tenant.id, kind="full", destination_path="/f",
            size_bytes=1, sha256_hex="1" * 64, encryption_key_label="x",
        )
        await record_backup(
            db, tenant_id=tenant.id, kind="verifactu", destination_path="/v",
            size_bytes=2, sha256_hex="2" * 64, encryption_key_label="vf",
        )
        await db.commit()

        full = await get_last_backup(db, tenant_id=tenant.id, kind="full")
        vf = await get_last_backup(db, tenant_id=tenant.id, kind="verifactu")
        assert full.destination_path == "/f"
        assert vf.destination_path == "/v"


class TestComputeFileSha256:
    def test_sha256_determinista(self):
        data = b"contenido del backup"
        h1 = compute_file_sha256(data)
        h2 = compute_file_sha256(data)
        assert h1 == h2
        assert len(h1) == 64


@pytest.mark.asyncio
class TestBackupStatusForBanner:
    async def test_sin_backups_muestra_banner(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        status = await backup_status_for_banner(db, tenant_id=tenant.id)
        assert status["has_any_backup"] is False
        assert status["show_banner"] is True
        assert status["stale"] is False  # no es stale si no hay
        assert status["days_since_last"] is None

    async def test_backup_reciente_no_muestra_banner(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        await record_backup(
            db, tenant_id=tenant.id, kind="full", destination_path="/r",
            size_bytes=10, sha256_hex="3" * 64, encryption_key_label="x",
        )
        await db.commit()

        status = await backup_status_for_banner(db, tenant_id=tenant.id)
        assert status["has_any_backup"] is True
        assert status["show_banner"] is False
        assert status["stale"] is False
        assert status["days_since_last"] == 0

    async def test_backup_viejo_es_stale(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        old = BackupRecord(
            tenant_id=tenant.id, kind="full", destination_path="/old",
            size_bytes=1, sha256_hex="o" * 64, encryption_key_label="x",
            created_at=datetime.now(UTC) - timedelta(days=BACKUP_STALE_THRESHOLD_DAYS + 3),
        )
        db.add(old)
        await db.commit()

        status = await backup_status_for_banner(db, tenant_id=tenant.id)
        assert status["stale"] is True
        assert status["show_banner"] is True
        assert status["days_since_last"] >= BACKUP_STALE_THRESHOLD_DAYS


@pytest.mark.asyncio
class TestBackupEndpoints:
    async def test_record_endpoint_requiere_auth(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/backup-local/record",
                json={
                    "kind": "full",
                    "destination_path": "/x",
                    "size_bytes": 1,
                    "sha256_hex": "0" * 64,
                    "encryption_key_label": "x",
                },
            )
        # Sin header Authorization, HTTPBearer(auto_error=True) responde 403.
        assert resp.status_code == 403

    async def test_record_endpoint_persiste(self, db, seed_tenant_and_user):
        _, _, token = seed_tenant_and_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/backup-local/record",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "kind": "full",
                    "destination_path": "C:/Users/X/backup.dump.enc",
                    "size_bytes": 12345,
                    "sha256_hex": "1" * 64,
                    "encryption_key_label": "user_master",
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["kind"] == "full"
        assert data["size_bytes"] == 12345

    async def test_record_rechaza_hash_invalido(self, db, seed_tenant_and_user):
        _, _, token = seed_tenant_and_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/backup-local/record",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "kind": "full",
                    "destination_path": "/x",
                    "size_bytes": 1,
                    "sha256_hex": "not-hex",  # inválido
                    "encryption_key_label": "x",
                },
            )
        assert resp.status_code == 422

    async def test_status_endpoint_devuelve_show_banner_true_sin_backups(self, db, seed_tenant_and_user):
        _, _, token = seed_tenant_and_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                "/api/v1/backup-local/status",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["show_banner"] is True
        assert data["has_any_backup"] is False
