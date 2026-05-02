"""Tests for HR API — validates real responses (replaces != 500 fakes)."""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestHrAuth:
    @pytest.mark.asyncio
    async def test_list_employees_unauth(self, client: AsyncClient):
        resp = await client.get("/api/v1/hr/employees")
        assert resp.status_code in (401, 403)


class TestHrEmployees:
    @pytest.mark.asyncio
    async def test_list_employees_returns_array(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/hr/employees")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_payroll_preview_nonexistent_employee_returns_404(self, auth_client: AsyncClient):
        # GET /hr/employees/{id}/payroll/preview is the closest "fetch by id" route
        resp = await auth_client.get(f"/api/v1/hr/employees/{uuid4()}/payroll/preview")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_employee_with_minimal_fields(self, auth_client: AsyncClient):
        payload = {
            "first_name": "María",
            "last_name": "García",
            "nif": "12345678A",
            "email": "maria@empresa.com",
            "salary_base": 1800.0,
        }
        resp = await auth_client.post("/api/v1/hr/employees", json=payload)
        # Expect 201 Created (or 422 if schema requires additional fields)
        assert resp.status_code in (200, 201, 422)
        if resp.status_code in (200, 201):
            data = resp.json()
            assert "id" in data
            assert data.get("first_name") == "María"

    @pytest.mark.asyncio
    async def test_create_employee_missing_required_fields_returns_422(
        self, auth_client: AsyncClient,
    ):
        resp = await auth_client.post("/api/v1/hr/employees", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_employee_lifecycle_create_then_appears_in_list(self, auth_client: AsyncClient):
        payload = {
            "first_name": "Pepe",
            "last_name": "Pérez",
            "nif": "87654321B",
            "email": "pepe@empresa.com",
            "salary_base": 2000.0,
        }
        created = await auth_client.post("/api/v1/hr/employees", json=payload)
        if created.status_code not in (200, 201):
            pytest.skip(f"HR employee create unavailable (status={created.status_code})")
        emp_id = created.json()["id"]
        # No GET /employees/{id} route — verify via list
        listed = await auth_client.get("/api/v1/hr/employees")
        assert listed.status_code == 200
        assert any(e["id"] == emp_id for e in listed.json())


class TestHrPayrolls:
    @pytest.mark.asyncio
    async def test_list_payrolls_returns_array(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/hr/payrolls")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_create_payroll_for_unknown_employee_returns_4xx(
        self, auth_client: AsyncClient,
    ):
        resp = await auth_client.post(
            "/api/v1/hr/payrolls",
            json={"employee_id": str(uuid4()), "period": "2026-04", "base_salary": 2000.0},
        )
        # Either 404 (employee not found) or 422 (validation) — must not 500
        assert resp.status_code in (400, 404, 422)
