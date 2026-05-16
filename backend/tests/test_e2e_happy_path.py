"""E2E Happy Path — flujos completos multi-endpoint.

Cada test verifica un journey realista de usuario que cruza varios
endpoints, en contraste con los tests unitarios por endpoint.
Sin LLM real: deterministas, rápidos, en SQLite en memoria.
"""
from datetime import datetime

import pytest
from httpx import AsyncClient


class TestAuthHappyPath:
    """Registro → login → endpoint protegido → refresh → nuevo token válido."""

    @pytest.mark.asyncio
    async def test_register_login_use_refresh(self, client: AsyncClient):
        # 1. Registro de nueva empresa y usuario admin
        reg = await client.post("/api/v1/auth/register", json={
            "email": "admin@miempresa.com",
            "password": "SecurePass123!",
            "full_name": "Admin Empresa",
            "tenant": {"name": "Mi Empresa S.L.", "nif": "B12300001"},
        })
        assert reg.status_code == 201, reg.text
        user = reg.json()
        assert user["email"] == "admin@miempresa.com"
        assert user["role"] == "admin"

        # 2. Login con credenciales → tokens
        login = await client.post("/api/v1/auth/login", json={
            "email": "admin@miempresa.com",
            "password": "SecurePass123!",
        })
        assert login.status_code == 200, login.text
        tokens = login.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # 3. Token válido en endpoint protegido
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        invoices = await client.get("/api/v1/invoices", headers=headers)
        assert invoices.status_code == 200
        assert invoices.json() == []  # nuevo tenant, sin facturas

        # 4. Refresh → nuevos tokens
        refresh = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert refresh.status_code == 200, refresh.text
        new_tokens = refresh.json()
        assert "access_token" in new_tokens

        # 5. Nuevo access token funciona
        new_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        check = await client.get("/api/v1/invoices", headers=new_headers)
        assert check.status_code == 200


class TestInvoiceLifecycle:
    """Cliente → factura borrador con líneas → enviada → verificada en listado."""

    @pytest.mark.asyncio
    async def test_full_invoice_lifecycle(self, auth_client: AsyncClient):
        # 1. Crear cliente
        client_resp = await auth_client.post("/api/v1/clients", json={
            "name": "Empresa Cliente S.A.",
            "nif": "A12345678",
            "email": "cliente@empresa.com",
        })
        assert client_resp.status_code == 201, client_resp.text
        client_id = client_resp.json()["id"]

        # 2. Factura en borrador con dos líneas
        create = await auth_client.post(
            f"/api/v1/clients/{client_id}/invoices",
            json={
                "date": datetime.now().isoformat(),
                "status": "draft",
                "invoice_type": "issued",
                "lines": [
                    {"description": "Desarrollo web", "quantity": 10.0,
                     "unit_price": 80.0, "tax_percentage": 21.0},
                    {"description": "Consultoría", "quantity": 2.0,
                     "unit_price": 150.0, "tax_percentage": 21.0},
                ],
            },
        )
        assert create.status_code == 201, create.text
        invoice = create.json()
        invoice_id = invoice["id"]
        assert invoice["status"] == "draft"
        assert invoice["client_id"] == client_id
        assert "invoice_number" in invoice

        # 3. Borrador recuperable por ID
        get = await auth_client.get(f"/api/v1/invoices/{invoice_id}")
        assert get.status_code == 200
        assert get.json()["status"] == "draft"

        # 4. Marcar como pendiente de cobro (enviada al cliente)
        send = await auth_client.patch(
            f"/api/v1/invoices/{invoice_id}/status",
            json={"status": "pending"},
        )
        assert send.status_code == 200, send.text
        assert send.json()["status"] == "pending"

        # 5. Aparece en listado general
        listing = await auth_client.get("/api/v1/invoices")
        assert listing.status_code == 200
        ids = [inv["id"] for inv in listing.json()]
        assert invoice_id in ids


class TestHROnboarding:
    """Alta de empleado → nómina del mes → nómina en listado."""

    @pytest.mark.asyncio
    async def test_employee_onboarding_and_first_payroll(self, auth_client: AsyncClient):
        # 1. Crear empleado
        emp = await auth_client.post("/api/v1/hr/employees", json={
            "name": "Ana García",
            "base_salary": 2500.0,
            "irpf_rate": 18.0,
        })
        assert emp.status_code == 201, emp.text
        emp_data = emp.json()
        emp_id = emp_data["id"]
        assert emp_data["name"] == "Ana García"

        # 2. Empleado visible en el listado
        employees = await auth_client.get("/api/v1/hr/employees")
        assert employees.status_code == 200
        emp_ids = [e["id"] for e in employees.json()]
        assert emp_id in emp_ids

        # 3. Primera nómina
        payroll = await auth_client.post("/api/v1/hr/payrolls", json={
            "employee_id": emp_id,
            "period_start": "2026-05-01T00:00:00",
            "period_end": "2026-05-31T23:59:59",
            "issue_date": "2026-06-01T00:00:00",
            "base_salary": 2500.0,
            "deductions": 450.0,
            "net_salary": 2050.0,
        })
        assert payroll.status_code == 201, payroll.text
        p = payroll.json()
        payroll_id = p["id"]
        assert p["employee_id"] == emp_id
        assert p["status"] == "draft"
        assert p["net_salary"] == 2050.0

        # 4. Nómina visible en el listado
        payrolls = await auth_client.get("/api/v1/hr/payrolls")
        assert payrolls.status_code == 200
        payroll_ids = [pr["id"] for pr in payrolls.json()]
        assert payroll_id in payroll_ids
