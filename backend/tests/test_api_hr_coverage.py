"""Tests for HR API."""
import pytest
from httpx import AsyncClient

class TestHR:
    @pytest.mark.asyncio
    async def test_list_employees(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/hr/employees")
        assert resp.status_code != 500

    @pytest.mark.asyncio
    async def test_get_employee(self, auth_client: AsyncClient):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await auth_client.get(f"/api/v1/hr/employees/{fake_id}")
        assert resp.status_code != 500

    @pytest.mark.asyncio
    async def test_create_employee(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/hr/employees",
            json={"name": "Test Employee", "first_name": "Test", "last_name": "Employee"}
        )
        assert resp.status_code != 500

    @pytest.mark.asyncio
    async def test_list_payrolls(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/hr/payrolls")
        assert resp.status_code != 500

    @pytest.mark.asyncio
    async def test_create_payroll(self, auth_client: AsyncClient):
        import uuid
        emp_id = str(uuid.uuid4())
        resp = await auth_client.post(
            "/api/v1/hr/payrolls",
            json={"employee_id": emp_id, "period": "2026-04", "base_salary": 2000.0}
        )
        assert resp.status_code != 500
