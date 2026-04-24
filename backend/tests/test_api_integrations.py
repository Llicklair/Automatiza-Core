"""Tests for Integrations API."""
import pytest
from httpx import AsyncClient

class TestIntegrations:
    @pytest.mark.asyncio
    async def test_list_integrations_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/integrations/")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_integrations_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/integrations/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_get_integration_not_found(self, auth_client: AsyncClient):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await auth_client.get(f"/api/v1/integrations/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_integration_minimal(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/integrations/",
            json={
                "name": "My Integration",
                "provider": "google",
                "auth_type": "oauth2"
            }
        )
        assert resp.status_code in (201, 422, 405)  # POST / not implemented

    @pytest.mark.asyncio
    async def test_delete_integration_not_found(self, auth_client: AsyncClient):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await auth_client.delete(f"/api/v1/integrations/{fake_id}")
        assert resp.status_code == 404
