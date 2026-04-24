"""Tests for Templates API."""
import pytest
from httpx import AsyncClient

class TestTemplates:
    @pytest.mark.asyncio
    async def test_list_templates(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/templates/")
        assert resp.status_code != 500

    @pytest.mark.asyncio
    async def test_create_template(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/templates/",
            json={"name": "Test Template", "content": "Hello {{name}}", "type": "email"}
        )
        assert resp.status_code != 500

    @pytest.mark.asyncio
    async def test_get_template(self, auth_client: AsyncClient):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await auth_client.get(f"/api/v1/templates/{fake_id}")
        assert resp.status_code != 500

    @pytest.mark.asyncio
    async def test_render_template(self, auth_client: AsyncClient):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await auth_client.post(f"/api/v1/templates/{fake_id}/render", json={"context": {"name": "World"}})
        assert resp.status_code != 500
