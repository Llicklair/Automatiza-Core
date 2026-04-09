"""Tests para endpoints Workflows /api/v1/workflows/*."""
import pytest
from httpx import AsyncClient


class TestWorkflows:
    @pytest.mark.asyncio
    async def test_list_workflows_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/workflows/")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_workflow(self, auth_client: AsyncClient):
        payload = {
            "name": "Factura recurrente mensual",
            "description": "Genera factura el dia 1 de cada mes",
            "trigger_type": "schedule_based",
            "trigger_config": {"cron": "0 9 1 * *"},
            "action_type": "create_task",
            "action_config": {"task_text": "Crear factura mensual cliente ACME"},
        }
        resp = await auth_client.post("/api/v1/workflows/", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Factura recurrente mensual"
        assert data["trigger_type"] == "schedule_based"
        assert data["is_active"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_workflow_missing_name(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/workflows/", json={
            "trigger_type": "manual",
            "action_type": "create_task",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_workflow_by_id(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/v1/workflows/", json={
            "name": "WF Test",
            "trigger_type": "manual",
            "action_type": "create_task",
            "action_config": {"task_text": "test"},
        })
        wf_id = create_resp.json()["id"]
        resp = await auth_client.get(f"/api/v1/workflows/{wf_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "WF Test"

    @pytest.mark.asyncio
    async def test_update_workflow(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/v1/workflows/", json={
            "name": "WF Update",
            "trigger_type": "event_based",
            "action_type": "email",
            "action_config": {},
        })
        wf_id = create_resp.json()["id"]
        resp = await auth_client.patch(f"/api/v1/workflows/{wf_id}", json={
            "name": "WF Updated",
            "trigger_type": "event_based",
            "action_type": "email",
            "is_active": False,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "WF Updated"
        assert resp.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_workflow(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/v1/workflows/", json={
            "name": "WF Delete",
            "trigger_type": "manual",
            "action_type": "create_task",
            "action_config": {},
        })
        wf_id = create_resp.json()["id"]
        resp = await auth_client.delete(f"/api/v1/workflows/{wf_id}")
        assert resp.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_workflows_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/workflows/")
        assert resp.status_code in (401, 403)
