"""Tests para el endpoint de telemetría (AI.REV)."""
import pytest
from app.db.models.auth import TelemetryOptOut
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


@pytest.mark.asyncio
class TestTelemetryEndpoint:
    async def test_get_status_default_no_opted_out(self, db, seed_tenant_and_user):
        _, _, token = seed_tenant_and_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                "/api/v1/telemetry/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["opted_out"] is False
        assert data["opted_out_at"] is None
        assert "per-incidente" in data["note"]

    async def test_revoke_marca_opted_out(self, db, seed_tenant_and_user):
        tenant, _, token = seed_tenant_and_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete(
                "/api/v1/telemetry/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["opted_out"] is True
        assert data["opted_out_at"] is not None
        assert data["purge_job_scheduled"] is True
        # Comprobar en BD
        result = await db.execute(
            select(TelemetryOptOut).where(TelemetryOptOut.tenant_id == tenant.id)
        )
        opt_out = result.scalar_one_or_none()
        assert opt_out is not None

    async def test_revoke_idempotente(self, db, seed_tenant_and_user):
        _, _, token = seed_tenant_and_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp1 = await ac.delete(
                "/api/v1/telemetry/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp2 = await ac.delete(
                "/api/v1/telemetry/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["purge_job_scheduled"] is True
        assert resp2.json()["purge_job_scheduled"] is False
        # Misma fecha en ambas respuestas — no se sobreescribe
        assert resp1.json()["opted_out_at"] == resp2.json()["opted_out_at"]

    async def test_status_tras_revoke_devuelve_opted_out(self, db, seed_tenant_and_user):
        _, _, token = seed_tenant_and_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.delete(
                "/api/v1/telemetry/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp = await ac.get(
                "/api/v1/telemetry/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["opted_out"] is True
        assert "desactivada" in data["note"]

    async def test_endpoint_requiere_auth(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp_get = await ac.get("/api/v1/telemetry/me")
            resp_del = await ac.delete("/api/v1/telemetry/me")
        # Sin header Authorization, HTTPBearer(auto_error=True) responde 403.
        assert resp_get.status_code == 403
        assert resp_del.status_code == 403
