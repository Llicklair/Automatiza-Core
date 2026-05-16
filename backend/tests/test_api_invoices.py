"""Tests para endpoints Invoices /api/v1/invoices/* and /api/v1/clients/{id}/invoices."""
from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestInvoicesNoAuth:
    @pytest.mark.asyncio
    async def test_list_invoices_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/invoices")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_invoice_no_auth(self, client: AsyncClient):
        fake_id = str(uuid4())
        resp = await client.post(f"/api/v1/clients/{fake_id}/invoices", json={})
        assert resp.status_code in (401, 403, 422)


class TestInvoices:
    async def _create_client(self, auth_client: AsyncClient) -> str:
        resp = await auth_client.post("/api/v1/clients", json={"name": "Cliente Factura"})
        assert resp.status_code == 201
        return resp.json()["id"]

    @pytest.mark.asyncio
    async def test_list_invoices_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/invoices")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_invoice(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        payload = {
            "date": datetime.now().isoformat(),
            "status": "draft",
            "invoice_type": "issued",
            "lines": [
                {
                    "description": "Servicio de consultoría",
                    "quantity": 2.0,
                    "unit_price": 100.0,
                    "tax_percentage": 21.0,
                }
            ],
        }
        resp = await auth_client.post(f"/api/v1/clients/{client_id}/invoices", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["client_id"] == client_id
        assert data["status"] == "draft"
        assert "id" in data
        assert "invoice_number" in data

    @pytest.mark.asyncio
    async def test_create_invoice_no_lines(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        payload = {
            "date": datetime.now().isoformat(),
        }
        resp = await auth_client.post(f"/api/v1/clients/{client_id}/invoices", json=payload)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_invoice_missing_date(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        resp = await auth_client.post(f"/api/v1/clients/{client_id}/invoices", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_invoice(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        create_resp = await auth_client.post(
            f"/api/v1/clients/{client_id}/invoices",
            json={"date": datetime.now().isoformat()},
        )
        invoice_id = create_resp.json()["id"]
        resp = await auth_client.get(f"/api/v1/invoices/{invoice_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == invoice_id

    @pytest.mark.asyncio
    async def test_get_invoice_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.get(f"/api/v1/invoices/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_invoice_status(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        create_resp = await auth_client.post(
            f"/api/v1/clients/{client_id}/invoices",
            json={"date": datetime.now().isoformat()},
        )
        invoice_id = create_resp.json()["id"]
        resp = await auth_client.patch(
            f"/api/v1/invoices/{invoice_id}/status", json={"status": "paid"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_update_invoice_status_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.patch(
            f"/api/v1/invoices/{fake_id}/status", json={"status": "paid"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_invoice(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        create_resp = await auth_client.post(
            f"/api/v1/clients/{client_id}/invoices",
            json={"date": datetime.now().isoformat()},
        )
        invoice_id = create_resp.json()["id"]
        resp = await auth_client.delete(f"/api/v1/invoices/{invoice_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_invoice_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.delete(f"/api/v1/invoices/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_invoices_after_create(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        await auth_client.post(
            f"/api/v1/clients/{client_id}/invoices",
            json={"date": datetime.now().isoformat()},
        )
        resp = await auth_client.get("/api/v1/invoices")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
