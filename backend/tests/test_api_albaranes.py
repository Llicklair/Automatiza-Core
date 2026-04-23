"""Tests para endpoints Albaranes /api/v1/albaranes/*."""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestAlbaranesNoAuth:
    @pytest.mark.asyncio
    async def test_list_albaranes_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/albaranes")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_albaran_no_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/albaranes", json={})
        assert resp.status_code in (401, 403)


class TestAlbaranes:
    async def _create_client(self, auth_client: AsyncClient) -> str:
        resp = await auth_client.post("/api/v1/clients", json={"name": "Cliente Albaran"})
        assert resp.status_code == 201
        return resp.json()["id"]

    @pytest.mark.asyncio
    async def test_list_albaranes_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/albaranes")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_albaran(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        payload = {
            "client_id": client_id,
            "notes": "Entrega parcial",
            "lines": [
                {
                    "description": "Cajas de producto A",
                    "quantity": 10.0,
                    "unit_price": 25.0,
                    "tax_percentage": 21.0,
                }
            ],
        }
        resp = await auth_client.post("/api/v1/albaranes", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["notes"] == "Entrega parcial"
        assert "id" in data
        assert "albaran_number" in data

    @pytest.mark.asyncio
    async def test_create_albaran_no_client(self, auth_client: AsyncClient):
        payload = {
            "notes": "Sin cliente",
            "lines": [
                {"description": "Producto genérico", "quantity": 1.0, "unit_price": 10.0}
            ],
        }
        resp = await auth_client.post("/api/v1/albaranes", json=payload)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_albaran_empty(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/albaranes", json={})
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_get_albaran(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            "/api/v1/albaranes",
            json={"lines": [{"description": "Item", "quantity": 1, "unit_price": 5}]},
        )
        albaran_id = create_resp.json()["id"]
        resp = await auth_client.get(f"/api/v1/albaranes/{albaran_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == albaran_id

    @pytest.mark.asyncio
    async def test_get_albaran_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.get(f"/api/v1/albaranes/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_albaran_status(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            "/api/v1/albaranes",
            json={"lines": [{"description": "Item", "quantity": 1, "unit_price": 10}]},
        )
        albaran_id = create_resp.json()["id"]
        resp = await auth_client.patch(
            f"/api/v1/albaranes/{albaran_id}/status", json={"status": "confirmed"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_update_albaran_status_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.patch(
            f"/api/v1/albaranes/{fake_id}/status", json={"status": "confirmed"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_albaran(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            "/api/v1/albaranes",
            json={"lines": [{"description": "Item", "quantity": 1, "unit_price": 5}]},
        )
        albaran_id = create_resp.json()["id"]
        resp = await auth_client.delete(f"/api/v1/albaranes/{albaran_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_albaran_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.delete(f"/api/v1/albaranes/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_albaranes_after_create(self, auth_client: AsyncClient):
        await auth_client.post(
            "/api/v1/albaranes",
            json={"lines": [{"description": "A", "quantity": 1, "unit_price": 1}]},
        )
        await auth_client.post(
            "/api/v1/albaranes",
            json={"lines": [{"description": "B", "quantity": 2, "unit_price": 2}]},
        )
        resp = await auth_client.get("/api/v1/albaranes")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
