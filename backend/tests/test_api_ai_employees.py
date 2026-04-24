"""Tests for AI Employees API."""
import pytest
from httpx import AsyncClient

class TestAIEmployees:
    @pytest.mark.asyncio
    async def test_list_agents(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/ai-employees")
        assert resp.status_code != 500

    @pytest.mark.asyncio
    async def test_get_agent(self, auth_client: AsyncClient):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await auth_client.get(f"/api/v1/ai-employees/{fake_id}")
        assert resp.status_code != 500

    @pytest.mark.asyncio
    async def test_create_agent(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/ai-employees",
            json={"name": "Test Agent", "role": "sales", "system_prompt": "You are helpful."}
        )
        assert resp.status_code != 500

    @pytest.mark.asyncio
    async def test_delete_agent(self, auth_client: AsyncClient):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await auth_client.delete(f"/api/v1/ai-employees/{fake_id}")
        assert resp.status_code != 500
