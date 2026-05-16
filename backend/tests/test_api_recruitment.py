"""Tests para endpoints Recruitment /api/v1/recruitment/*."""
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestRecruitmentPositions:
    @pytest.mark.asyncio
    async def test_list_positions_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/recruitment/positions")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_position(self, auth_client: AsyncClient):
        payload = {
            "title": "Desarrollador Python Senior",
            "department": "Ingenieria",
            "description": "Desarrollo backend con FastAPI",
            "required_skills": ["python", "fastapi", "postgresql"],
            "experience_min_years": 3,
        }
        resp = await auth_client.post("/api/v1/recruitment/positions", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Desarrollador Python Senior"
        assert data["department"] == "Ingenieria"
        assert "id" in data
        assert data["status"] == "open"

    @pytest.mark.asyncio
    async def test_create_position_minimal(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/recruitment/positions", json={
            "title": "Puesto minimo",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Puesto minimo"

    @pytest.mark.asyncio
    async def test_create_position_missing_title(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/recruitment/positions", json={
            "department": "RRHH",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_positions_after_create(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/recruitment/positions", json={
            "title": "Analista Datos",
        })
        resp = await auth_client.get("/api/v1/recruitment/positions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["title"] == "Analista Datos"

    @pytest.mark.asyncio
    async def test_positions_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/recruitment/positions")
        assert resp.status_code in (401, 403)


class TestRecruitmentCandidates:
    @pytest.mark.asyncio
    async def test_list_candidates_empty(self, auth_client: AsyncClient):
        # First create a position
        pos_resp = await auth_client.post("/api/v1/recruitment/positions", json={
            "title": "Frontend Dev",
        })
        pos_id = pos_resp.json()["id"]

        resp = await auth_client.get(f"/api/v1/recruitment/positions/{pos_id}/candidates")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_candidates_invalid_position(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.get(f"/api/v1/recruitment/positions/{fake_id}/candidates")
        # Should return 200 with empty list or 404 depending on implementation
        assert resp.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_candidates_require_auth(self, client: AsyncClient):
        fake_id = str(uuid4())
        resp = await client.get(f"/api/v1/recruitment/positions/{fake_id}/candidates")
        assert resp.status_code in (401, 403)
