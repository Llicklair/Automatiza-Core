"""Tests para endpoints Admin /api/v1/admin/*."""
import pytest
from httpx import AsyncClient


class TestAdmin:
    @pytest.mark.asyncio
    async def test_backup_fails_in_test_env(self, auth_client: AsyncClient):
        """Backup uses pg_dump which is not available against SQLite test DB.
        Missing pg_dump is a missing-dependency condition, so the endpoint
        returns 503 (Service Unavailable), not 500."""
        resp = await auth_client.get("/api/v1/admin/backup")
        # In test environment pg_dump is absent → 503 (dependency unavailable)
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_restore_requires_sql_file(self, auth_client: AsyncClient):
        """Upload a non-.sql file should be rejected."""
        import io
        files = {"file": ("data.txt", io.BytesIO(b"not sql"), "text/plain")}
        resp = await auth_client.post("/api/v1/admin/restore", files=files)
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_restore_empty_sql_file(self, auth_client: AsyncClient):
        """Upload an empty .sql file should be rejected (too small)."""
        import io
        files = {"file": ("backup.sql", io.BytesIO(b""), "application/octet-stream")}
        resp = await auth_client.post("/api/v1/admin/restore", files=files)
        # Empty content should fail validation (file too small or not valid SQL)
        assert resp.status_code in (400, 422, 500)

    @pytest.mark.asyncio
    async def test_backup_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/backup")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_restore_requires_auth(self, client: AsyncClient):
        import io
        files = {"file": ("backup.sql", io.BytesIO(b"-- SQL"), "application/octet-stream")}
        resp = await client.post("/api/v1/admin/restore", files=files)
        assert resp.status_code in (401, 403)
