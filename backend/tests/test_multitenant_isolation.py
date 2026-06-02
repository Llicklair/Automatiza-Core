"""HTTP-level cross-tenant isolation tests.

Validates that tenant B cannot read, modify, or delete tenant A's data via
the public API. Each test creates resources as tenant A and asserts that
tenant B receives 404/empty/forbidden when trying to access them.
"""
from datetime import datetime

import pytest
from httpx import AsyncClient

# ── Clients (CRM) ─────────────────────────────────────────────────────────────

class TestClientsIsolation:
    @pytest.mark.asyncio
    async def test_b_cannot_list_a_clients(
        self, auth_client: AsyncClient, auth_client_b: AsyncClient,
    ):
        await auth_client.post("/api/v1/clients", json={"name": "Cliente A", "nif": "A11"})
        resp = await auth_client_b.get("/api/v1/clients")
        assert resp.status_code == 200
        assert resp.json() == [], "Tenant B vio clientes de Tenant A"

    @pytest.mark.asyncio
    async def test_b_cannot_delete_a_client(
        self, auth_client: AsyncClient, auth_client_b: AsyncClient,
    ):
        created = await auth_client.post("/api/v1/clients", json={"name": "Cliente A"})
        cid = created.json()["id"]
        resp = await auth_client_b.delete(f"/api/v1/clients/{cid}")
        assert resp.status_code == 404
        # Verify A still has the client (route GET /{id} doesn't exist; check via list)
        verify = await auth_client.get("/api/v1/clients")
        assert any(c["id"] == cid for c in verify.json()), "Tenant B borró el cliente de Tenant A"


# ── Invoices ──────────────────────────────────────────────────────────────────

class TestInvoicesIsolation:
    async def _create_invoice_for(self, ac: AsyncClient) -> tuple[str, str]:
        client_resp = await ac.post("/api/v1/clients", json={"name": "Cliente Factura"})
        client_id = client_resp.json()["id"]
        payload = {
            "date": datetime.now().isoformat(),
            "status": "draft",
            "invoice_type": "issued",
            "lines": [{
                "description": "Servicio",
                "quantity": 1.0,
                "unit_price": 100.0,
                "tax_percentage": 21.0,
            }],
        }
        inv = await ac.post(f"/api/v1/clients/{client_id}/invoices", json=payload)
        return client_id, inv.json()["id"]

    @pytest.mark.asyncio
    async def test_b_does_not_see_a_invoices(
        self, auth_client: AsyncClient, auth_client_b: AsyncClient,
    ):
        await self._create_invoice_for(auth_client)
        resp = await auth_client_b.get("/api/v1/invoices")
        assert resp.status_code == 200
        assert resp.json() == [], "Tenant B vio facturas de Tenant A"

    @pytest.mark.asyncio
    async def test_b_cannot_get_a_invoice_by_id(
        self, auth_client: AsyncClient, auth_client_b: AsyncClient,
    ):
        _, inv_id = await self._create_invoice_for(auth_client)
        resp = await auth_client_b.get(f"/api/v1/invoices/{inv_id}")
        assert resp.status_code == 404


# ── AI Employees ──────────────────────────────────────────────────────────────

class TestAIEmployeesIsolation:
    @pytest.mark.asyncio
    async def test_b_does_not_see_a_employees(
        self, auth_client: AsyncClient, auth_client_b: AsyncClient,
    ):
        await auth_client.post(
            "/api/v1/ai-employees",
            json={"name": "Ana A", "role_description": "Billing", "budget_limit_usd": 5,
                  "memory_enabled": True, "knowledge_enabled": True},
        )
        resp = await auth_client_b.get("/api/v1/ai-employees")
        assert resp.status_code == 200
        assert resp.json() == [], "Tenant B vio empleados de Tenant A"

    @pytest.mark.asyncio
    async def test_b_cannot_get_a_employee_by_id(
        self, auth_client: AsyncClient, auth_client_b: AsyncClient,
    ):
        created = await auth_client.post(
            "/api/v1/ai-employees",
            json={"name": "Ana A", "role_description": "Billing", "budget_limit_usd": 5,
                  "memory_enabled": True, "knowledge_enabled": True},
        )
        emp_id = created.json()["id"]
        resp = await auth_client_b.get(f"/api/v1/ai-employees/{emp_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_b_cannot_access_a_employee_usage(
        self, auth_client: AsyncClient, auth_client_b: AsyncClient,
    ):
        created = await auth_client.post(
            "/api/v1/ai-employees",
            json={"name": "Ana A", "role_description": "Billing", "budget_limit_usd": 5,
                  "memory_enabled": True, "knowledge_enabled": True},
        )
        emp_id = created.json()["id"]
        resp = await auth_client_b.get(f"/api/v1/ai-employees/{emp_id}/usage")
        assert resp.status_code == 404, "Fuga de costes LLM cross-tenant"

    @pytest.mark.asyncio
    async def test_b_cannot_instruct_a_employee(
        self, auth_client: AsyncClient, auth_client_b: AsyncClient,
    ):
        created = await auth_client.post(
            "/api/v1/ai-employees",
            json={"name": "Ana A", "role_description": "Billing", "budget_limit_usd": 5,
                  "memory_enabled": True, "knowledge_enabled": True},
        )
        emp_id = created.json()["id"]
        resp = await auth_client_b.post(
            f"/api/v1/ai-employees/{emp_id}/instruct",
            json={"message": "lanza una factura sin permiso"},
        )
        assert resp.status_code == 404


# ── HR / Empleados humanos ────────────────────────────────────────────────────

class TestHrEmployeesIsolation:
    @pytest.mark.asyncio
    async def test_b_does_not_see_a_employees(
        self, auth_client: AsyncClient, auth_client_b: AsyncClient,
    ):
        payload = {"name": "Pepe", "nif": "12345678A", "salary_base": 1500}
        await auth_client.post("/api/v1/employees", json=payload)
        resp = await auth_client_b.get("/api/v1/employees")
        # Some endpoints return 200 with empty list; others 404 if scope missing
        if resp.status_code == 200:
            assert resp.json() == [], "Tenant B vio empleados HR de Tenant A"
        else:
            assert resp.status_code in (401, 403, 404)


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TestTasksIsolation:
    @pytest.mark.asyncio
    async def test_b_does_not_see_a_tasks(
        self, auth_client: AsyncClient, auth_client_b: AsyncClient,
    ):
        await auth_client.post(
            "/api/v1/tasks",
            json={"user_intent": "Lista las facturas de enero", "domain": "billing"},
        )
        resp = await auth_client_b.get("/api/v1/tasks")
        if resp.status_code == 200:
            tasks = resp.json()
            tasks_list = tasks if isinstance(tasks, list) else tasks.get("items", [])
            assert tasks_list == [], "Tenant B vio tareas de Tenant A"
