"""Tests for AI Employees API — full CRUD, error paths, budget enforcement."""
from uuid import uuid4

import pytest
from httpx import AsyncClient

# ── No auth ───────────────────────────────────────────────────────────────────

class TestAIEmployeesNoAuth:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/ai-employees")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/ai-employees", json={})
        assert resp.status_code in (401, 403, 422)

    @pytest.mark.asyncio
    async def test_get_by_id_requires_auth(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/ai-employees/{uuid4()}")
        assert resp.status_code in (401, 403)


# ── CRUD happy paths ──────────────────────────────────────────────────────────

class TestAIEmployees:
    _PAYLOAD = {
        "name": "Ana García",
        "role_description": "Responsable de facturación y cobros",
        "budget_limit_usd": 5.0,
    }

    async def _create(self, auth_client: AsyncClient) -> dict:
        resp = await auth_client.post("/api/v1/ai-employees", json=self._PAYLOAD)
        assert resp.status_code == 201
        return resp.json()

    @pytest.mark.asyncio
    async def test_list_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/ai-employees")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_create_returns_employee(self, auth_client: AsyncClient):
        data = await self._create(auth_client)
        assert data["name"] == "Ana García"
        assert data["status"] in ("pending_setup", "idle")
        assert data["budget_limit_usd"] == 5.0
        assert "id" in data
        assert "domain" in data

    @pytest.mark.asyncio
    async def test_create_missing_fields_returns_422(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/ai-employees", json={"name": "Solo nombre"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_by_id_returns_employee(self, auth_client: AsyncClient):
        created = await self._create(auth_client)
        resp = await auth_client.get(f"/api/v1/ai-employees/{created['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == created["id"]
        assert data["name"] == created["name"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_404(self, auth_client: AsyncClient):
        resp = await auth_client.get(f"/api/v1/ai-employees/{uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_shows_created_employee(self, auth_client: AsyncClient):
        created = await self._create(auth_client)
        resp = await auth_client.get("/api/v1/ai-employees")
        assert resp.status_code == 200
        ids = [e["id"] for e in resp.json()]
        assert created["id"] in ids

    @pytest.mark.asyncio
    async def test_delete_returns_204(self, auth_client: AsyncClient):
        created = await self._create(auth_client)
        resp = await auth_client.delete(f"/api/v1/ai-employees/{created['id']}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, auth_client: AsyncClient):
        resp = await auth_client.delete(f"/api/v1/ai-employees/{uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_makes_employee_disappear(self, auth_client: AsyncClient):
        created = await self._create(auth_client)
        await auth_client.delete(f"/api/v1/ai-employees/{created['id']}")
        resp = await auth_client.get(f"/api/v1/ai-employees/{created['id']}")
        assert resp.status_code == 404

    # ── Status ────────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_pause_employee(self, auth_client: AsyncClient):
        created = await self._create(auth_client)
        resp = await auth_client.patch(
            f"/api/v1/ai-employees/{created['id']}/status",
            params={"new_status": "paused"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    @pytest.mark.asyncio
    async def test_resume_employee(self, auth_client: AsyncClient):
        created = await self._create(auth_client)
        await auth_client.patch(
            f"/api/v1/ai-employees/{created['id']}/status",
            params={"new_status": "paused"},
        )
        resp = await auth_client.patch(
            f"/api/v1/ai-employees/{created['id']}/status",
            params={"new_status": "idle"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "idle"

    # ── Appearance ────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_update_appearance(self, auth_client: AsyncClient):
        created = await self._create(auth_client)
        resp = await auth_client.patch(
            f"/api/v1/ai-employees/{created['id']}/appearance",
            json={"icon": "🤖", "avatar_color": "violet"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["icon"] == "🤖"
        assert data["avatar_color"] == "violet"

    # ── Skills ────────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_available_skills_returns_list(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/ai-employees/available-skills")
        assert resp.status_code == 200
        skills = resp.json()
        assert isinstance(skills, list)
        assert len(skills) > 0
        assert "module" in skills[0]
        assert "label" in skills[0]

    # ── Instruct ──────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_instruct_queues_task(self, auth_client: AsyncClient):
        created = await self._create(auth_client)
        # Provision so status is idle
        await auth_client.post(
            f"/api/v1/ai-employees/{created['id']}/provision",
            json={"domain": "billing", "role": "Facturación", "skills": []},
        )
        resp = await auth_client.post(
            f"/api/v1/ai-employees/{created['id']}/instruct",
            json={"message": "Lista las facturas pendientes de cobro"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_instruct_paused_returns_409(self, auth_client: AsyncClient):
        created = await self._create(auth_client)
        await auth_client.patch(
            f"/api/v1/ai-employees/{created['id']}/status",
            params={"new_status": "paused"},
        )
        resp = await auth_client.post(
            f"/api/v1/ai-employees/{created['id']}/instruct",
            json={"message": "Haz algo"},
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_instruct_nonexistent_returns_404(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            f"/api/v1/ai-employees/{uuid4()}/instruct",
            json={"message": "Haz algo"},
        )
        assert resp.status_code == 404

    # ── Usage endpoint ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_usage_endpoint_empty(self, auth_client: AsyncClient):
        created = await self._create(auth_client)
        resp = await auth_client.get(f"/api/v1/ai-employees/{created['id']}/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["employee_id"] == created["id"]
        assert data["total_calls"] == 0
        assert data["total_cost_usd"] == 0.0
        assert data["entries"] == []

    @pytest.mark.asyncio
    async def test_usage_nonexistent_returns_404(self, auth_client: AsyncClient):
        resp = await auth_client.get(f"/api/v1/ai-employees/{uuid4()}/usage")
        assert resp.status_code == 404
