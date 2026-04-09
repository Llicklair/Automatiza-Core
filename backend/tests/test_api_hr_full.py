"""Tests para endpoints HR /api/v1/hr/*."""
import pytest
from httpx import AsyncClient


class TestEmployees:
    @pytest.mark.asyncio
    async def test_list_employees_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/hr/employees")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_employee(self, auth_client: AsyncClient):
        payload = {
            "name": "Maria Garcia",
            "email": "maria@empresa.com",
            "nif": "12345678Z",
            "department": "Ventas",
            "role": "Comercial",
            "base_salary": 30000.0,
            "irpf_rate": 15.0,
        }
        resp = await auth_client.post("/api/v1/hr/employees", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Maria Garcia"
        assert data["department"] == "Ventas"
        assert data["base_salary"] == 30000.0
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_employee_minimal(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/hr/employees", json={"name": "Juan"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Juan"

    @pytest.mark.asyncio
    async def test_create_employee_missing_name(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/hr/employees", json={"email": "test@test.com"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_employee(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/v1/hr/employees", json={"name": "Ana"})
        emp_id = create_resp.json()["id"]
        resp = await auth_client.patch(f"/api/v1/hr/employees/{emp_id}", json={
            "department": "IT",
            "base_salary": 35000.0,
        })
        assert resp.status_code == 200
        assert resp.json()["department"] == "IT"

    @pytest.mark.asyncio
    async def test_employees_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/hr/employees")
        assert resp.status_code in (401, 403)


class TestPayrolls:
    @pytest.mark.asyncio
    async def test_list_payrolls_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/hr/payrolls")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_payroll(self, auth_client: AsyncClient):
        # Crear empleado primero
        emp_resp = await auth_client.post("/api/v1/hr/employees", json={
            "name": "Nomina Test",
            "base_salary": 2000.0,
            "irpf_rate": 15.0,
        })
        emp_id = emp_resp.json()["id"]

        payload = {
            "employee_id": emp_id,
            "period_start": "2026-03-01T00:00:00",
            "period_end": "2026-03-31T23:59:59",
            "issue_date": "2026-04-01T00:00:00",
            "base_salary": 2000.0,
            "deductions": 400.0,
            "net_salary": 1600.0,
        }
        resp = await auth_client.post("/api/v1/hr/payrolls", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["base_salary"] == 2000.0
        assert data["status"] == "draft"
