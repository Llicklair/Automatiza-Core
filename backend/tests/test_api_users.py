"""Tests for Users API."""
import pytest
from httpx import AsyncClient

class TestUsers:
    @pytest.mark.asyncio
    async def test_list_users_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/users")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_users_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/users")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_create_user(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/users",
            json={
                "email": "newuser@example.com",
                "password": "Password123!",
                "first_name": "New",
                "last_name": "User",
                "role": "user"
            }
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_get_user_me(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/users/me")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, auth_client: AsyncClient):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await auth_client.get(f"/api/v1/users/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, auth_client: AsyncClient):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await auth_client.patch(f"/api/v1/users/{fake_id}", json={"first_name": "Updated"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, auth_client: AsyncClient):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await auth_client.delete(f"/api/v1/users/{fake_id}")
        assert resp.status_code == 404
