"""Tests para endpoints Clients /api/v1/clients/*."""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestClientsNoAuth:
    @pytest.mark.asyncio
    async def test_list_clients_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/clients")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_client_no_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/clients", json={"name": "Test"})
        assert resp.status_code in (401, 403)


class TestClients:
    @pytest.mark.asyncio
    async def test_list_clients_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/clients")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_client(self, auth_client: AsyncClient):
        payload = {
            "name": "Empresa ABC S.L.",
            "nif": "B99999999",
            "email": "abc@empresa.com",
            "phone": "612345678",
            "address": "Calle Mayor 1",
            "city": "Madrid",
            "postal_code": "28001",
            "client_type": "customer",
        }
        resp = await auth_client.post("/api/v1/clients", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Empresa ABC S.L."
        assert data["nif"] == "B99999999"
        assert data["client_type"] == "customer"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_client_minimal(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/clients", json={"name": "Solo Nombre"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Solo Nombre"

    @pytest.mark.asyncio
    async def test_create_client_missing_name(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/clients", json={"nif": "B11111111"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_clients_after_create(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/clients", json={"name": "Cliente Uno"})
        await auth_client.post("/api/v1/clients", json={"name": "Cliente Dos"})
        resp = await auth_client.get("/api/v1/clients")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_update_client(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/v1/clients", json={"name": "Original"})
        client_id = create_resp.json()["id"]
        resp = await auth_client.patch(
            f"/api/v1/clients/{client_id}", json={"name": "Actualizado", "city": "Barcelona"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Actualizado"
        assert resp.json()["city"] == "Barcelona"

    @pytest.mark.asyncio
    async def test_update_client_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.patch(f"/api/v1/clients/{fake_id}", json={"name": "X"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_client(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/v1/clients", json={"name": "A Borrar"})
        client_id = create_resp.json()["id"]
        resp = await auth_client.delete(f"/api/v1/clients/{client_id}")
        assert resp.status_code == 204
        # Verify it's gone
        list_resp = await auth_client.get("/api/v1/clients")
        assert len(list_resp.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_client_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.delete(f"/api/v1/clients/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_client_invoices_empty(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/v1/clients", json={"name": "Con Facturas"})
        client_id = create_resp.json()["id"]
        resp = await auth_client.get(f"/api/v1/clients/{client_id}/invoices")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_clients_filter_type(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/clients", json={"name": "Proveedor X", "client_type": "supplier"})
        await auth_client.post("/api/v1/clients", json={"name": "Cliente Y", "client_type": "customer"})
        resp = await auth_client.get("/api/v1/clients?client_type=supplier")
        assert resp.status_code == 200
        data = resp.json()
        assert all(c["client_type"] == "supplier" for c in data)
