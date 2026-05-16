"""Tests para endpoints Albaranes /api/v1/albaranes/*."""
from uuid import uuid4

import pytest
from httpx import AsyncClient


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


class TestAlbaranesStockDeduction:
    async def _create_product(
        self, auth_client: AsyncClient, name: str, stock: int
    ) -> str:
        resp = await auth_client.post(
            "/api/v1/products",
            json={"name": name, "price": 10.0, "stock_quantity": stock},
        )
        assert resp.status_code == 201, resp.text
        return resp.json()["id"]

    async def _create_albaran_with_product(
        self, auth_client: AsyncClient, product_id: str, quantity: int
    ) -> str:
        resp = await auth_client.post(
            "/api/v1/albaranes",
            json={
                "lines": [
                    {
                        "product_id": product_id,
                        "description": "Línea con producto",
                        "quantity": quantity,
                        "unit_price": 10.0,
                    }
                ]
            },
        )
        assert resp.status_code == 201, resp.text
        return resp.json()["id"]

    @pytest.mark.asyncio
    async def test_confirm_deducts_stock(self, auth_client: AsyncClient):
        product_id = await self._create_product(auth_client, "Prod-A", stock=10)
        albaran_id = await self._create_albaran_with_product(
            auth_client, product_id, quantity=3
        )

        resp = await auth_client.patch(
            f"/api/v1/albaranes/{albaran_id}/status", json={"status": "confirmed"}
        )
        assert resp.status_code == 200

        mov_resp = await auth_client.get(
            f"/api/v1/products/{product_id}/stock-movements"
        )
        movs = mov_resp.json()
        assert len(movs) == 1
        assert movs[0]["movement_type"] == "salida"
        assert movs[0]["quantity"] == 3
        assert movs[0]["stock_after"] == 7
        assert movs[0]["reference"] == f"DELIVERY_NOTE:{albaran_id}"

    @pytest.mark.asyncio
    async def test_confirm_is_idempotent(self, auth_client: AsyncClient):
        product_id = await self._create_product(auth_client, "Prod-B", stock=10)
        albaran_id = await self._create_albaran_with_product(
            auth_client, product_id, quantity=2
        )

        first = await auth_client.patch(
            f"/api/v1/albaranes/{albaran_id}/status", json={"status": "confirmed"}
        )
        assert first.status_code == 200
        second = await auth_client.patch(
            f"/api/v1/albaranes/{albaran_id}/status", json={"status": "confirmed"}
        )
        assert second.status_code == 200

        mov_resp = await auth_client.get(
            f"/api/v1/products/{product_id}/stock-movements"
        )
        assert len(mov_resp.json()) == 1

    @pytest.mark.asyncio
    async def test_insufficient_stock_blocks_confirm(self, auth_client: AsyncClient):
        product_id = await self._create_product(auth_client, "Prod-C", stock=2)
        albaran_id = await self._create_albaran_with_product(
            auth_client, product_id, quantity=5
        )

        resp = await auth_client.patch(
            f"/api/v1/albaranes/{albaran_id}/status", json={"status": "confirmed"}
        )
        assert resp.status_code == 400
        assert "insuficiente" in resp.json()["detail"].lower()

        mov_resp = await auth_client.get(
            f"/api/v1/products/{product_id}/stock-movements"
        )
        assert mov_resp.json() == []

    @pytest.mark.asyncio
    async def test_delivered_after_confirmed_no_double_deduction(
        self, auth_client: AsyncClient
    ):
        product_id = await self._create_product(auth_client, "Prod-D", stock=10)
        albaran_id = await self._create_albaran_with_product(
            auth_client, product_id, quantity=4
        )
        await auth_client.patch(
            f"/api/v1/albaranes/{albaran_id}/status", json={"status": "confirmed"}
        )
        resp = await auth_client.patch(
            f"/api/v1/albaranes/{albaran_id}/status", json={"status": "delivered"}
        )
        assert resp.status_code == 200

        mov_resp = await auth_client.get(
            f"/api/v1/products/{product_id}/stock-movements"
        )
        assert len(mov_resp.json()) == 1

    @pytest.mark.asyncio
    async def test_line_without_product_id_skips_deduction(
        self, auth_client: AsyncClient
    ):
        create = await auth_client.post(
            "/api/v1/albaranes",
            json={
                "lines": [
                    {"description": "Servicio descriptivo", "quantity": 1, "unit_price": 50}
                ]
            },
        )
        albaran_id = create.json()["id"]
        resp = await auth_client.patch(
            f"/api/v1/albaranes/{albaran_id}/status", json={"status": "confirmed"}
        )
        assert resp.status_code == 200
