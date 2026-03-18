"""Tests para endpoints de sistema (/health, /)."""
import pytest
from httpx import AsyncClient


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_response(self, client: AsyncClient):
        resp = await client.get("/health")
        # En entorno de test sin Postgres real puede ser 200 o 503
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert "version" in data
        assert "checks" in data
        assert "postgres" in data["checks"]
        assert "status" in data["checks"]["postgres"]
        assert data["checks"]["postgres"]["status"] in ("up", "down")

    @pytest.mark.asyncio
    async def test_health_up_reports_latency(self, client: AsyncClient):
        """Si un servicio está up, debe reportar latencia."""
        resp = await client.get("/health")
        data = resp.json()
        if data["checks"]["postgres"]["status"] == "up":
            assert "latency_ms" in data["checks"]["postgres"]
            assert data["checks"]["postgres"]["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_root_returns_info(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "docs" in data
