"""Tests para endpoints Projects /api/v1/projects/*."""
import pytest
from httpx import AsyncClient


class TestProjects:
    @pytest.mark.asyncio
    async def test_list_projects_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/projects")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_project(self, auth_client: AsyncClient):
        payload = {
            "name": "Proyecto Web Corporativa",
            "description": "Desarrollo web cliente ACME",
            "budget": 12000.0,
            "status": "active",
        }
        resp = await auth_client.post("/api/v1/projects", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Proyecto Web Corporativa"
        assert data["budget"] == 12000.0
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_project_minimal(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/projects", json={"name": "Proyecto minimo"})
        assert resp.status_code == 201
        assert resp.json()["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_project_missing_name(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/projects", json={"budget": 5000.0})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_projects_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/projects")
        assert resp.status_code in (401, 403)


class TestProjectTasks:
    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/projects/tasks")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_task_standalone(self, auth_client: AsyncClient):
        payload = {
            "title": "Tarea independiente",
            "description": "Sin proyecto asociado",
            "status": "todo",
        }
        resp = await auth_client.post("/api/v1/projects/tasks", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Tarea independiente"
        assert data["project_id"] is None

    @pytest.mark.asyncio
    async def test_create_task_in_project(self, auth_client: AsyncClient):
        proj_resp = await auth_client.post("/api/v1/projects", json={"name": "Proj"})
        proj_id = proj_resp.json()["id"]
        payload = {
            "project_id": proj_id,
            "title": "Tarea del proyecto",
            "status": "todo",
        }
        resp = await auth_client.post("/api/v1/projects/tasks", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Tarea del proyecto"

    @pytest.mark.asyncio
    async def test_create_task_missing_title(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/projects/tasks", json={"status": "todo"})
        assert resp.status_code == 422
