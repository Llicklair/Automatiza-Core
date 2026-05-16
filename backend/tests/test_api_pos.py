"""Tests para endpoints TPV /api/v1/pos/*."""
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestPosNoAuth:
    @pytest.mark.asyncio
    async def test_current_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/pos/sessions/current")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_open_no_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/pos/sessions")
        assert resp.status_code in (401, 403)


class TestPosSessions:
    async def _create_product(
        self, auth_client: AsyncClient, name: str, stock: int, price: float = 10.0
    ) -> str:
        resp = await auth_client.post(
            "/api/v1/products",
            json={"name": name, "price": price, "stock_quantity": stock},
        )
        assert resp.status_code == 201, resp.text
        return resp.json()["id"]

    @pytest.mark.asyncio
    async def test_current_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/pos/sessions/current")
        assert resp.status_code == 200
        assert resp.json() is None

    @pytest.mark.asyncio
    async def test_open_session(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/pos/sessions")
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "open"
        assert data["lines"] == []
        assert data["payment_method"] is None

    @pytest.mark.asyncio
    async def test_cannot_open_two_sessions(self, auth_client: AsyncClient):
        first = await auth_client.post("/api/v1/pos/sessions")
        assert first.status_code == 201
        second = await auth_client.post("/api/v1/pos/sessions")
        assert second.status_code == 400
        assert "abierta" in second.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_add_line_with_product(self, auth_client: AsyncClient):
        product_id = await self._create_product(auth_client, "Prod-A", stock=10, price=15.0)
        sess = await auth_client.post("/api/v1/pos/sessions")
        session_id = sess.json()["id"]

        resp = await auth_client.post(
            f"/api/v1/pos/sessions/{session_id}/lines",
            json={"product_id": product_id, "quantity": 2},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["lines"]) == 1
        line = data["lines"][0]
        assert line["description"] == "Prod-A"
        assert line["unit_price"] == 15.0
        assert line["quantity"] == 2
        # total con IVA 21% = 2 * 15 * 1.21 = 36.30
        assert line["total"] == pytest.approx(36.30, abs=0.01)

    @pytest.mark.asyncio
    async def test_add_line_freetext(self, auth_client: AsyncClient):
        sess = await auth_client.post("/api/v1/pos/sessions")
        session_id = sess.json()["id"]

        resp = await auth_client.post(
            f"/api/v1/pos/sessions/{session_id}/lines",
            json={
                "description": "Servicio puntual",
                "quantity": 1,
                "unit_price": 50.0,
                "tax_percentage": 21.0,
            },
        )
        assert resp.status_code == 201
        line = resp.json()["lines"][0]
        assert line["product_id"] is None
        assert line["description"] == "Servicio puntual"

    @pytest.mark.asyncio
    async def test_update_line_quantity(self, auth_client: AsyncClient):
        product_id = await self._create_product(auth_client, "Prod-B", stock=10, price=10.0)
        sess = await auth_client.post("/api/v1/pos/sessions")
        session_id = sess.json()["id"]
        add_resp = await auth_client.post(
            f"/api/v1/pos/sessions/{session_id}/lines",
            json={"product_id": product_id, "quantity": 1},
        )
        line_id = add_resp.json()["lines"][0]["id"]

        upd = await auth_client.patch(
            f"/api/v1/pos/sessions/{session_id}/lines/{line_id}",
            json={"quantity": 5},
        )
        assert upd.status_code == 200
        line = upd.json()["lines"][0]
        assert line["quantity"] == 5
        # 5 * 10 * 1.21 = 60.5
        assert line["total"] == pytest.approx(60.5, abs=0.01)

    @pytest.mark.asyncio
    async def test_remove_line(self, auth_client: AsyncClient):
        product_id = await self._create_product(auth_client, "Prod-C", stock=10)
        sess = await auth_client.post("/api/v1/pos/sessions")
        session_id = sess.json()["id"]
        add_resp = await auth_client.post(
            f"/api/v1/pos/sessions/{session_id}/lines",
            json={"product_id": product_id, "quantity": 1},
        )
        line_id = add_resp.json()["lines"][0]["id"]

        resp = await auth_client.delete(
            f"/api/v1/pos/sessions/{session_id}/lines/{line_id}"
        )
        assert resp.status_code == 200
        assert resp.json()["lines"] == []

    @pytest.mark.asyncio
    async def test_checkout_deducts_stock_and_closes(self, auth_client: AsyncClient):
        product_id = await self._create_product(auth_client, "Prod-D", stock=10, price=10.0)
        sess = await auth_client.post("/api/v1/pos/sessions")
        session_id = sess.json()["id"]
        await auth_client.post(
            f"/api/v1/pos/sessions/{session_id}/lines",
            json={"product_id": product_id, "quantity": 3},
        )

        resp = await auth_client.post(
            f"/api/v1/pos/sessions/{session_id}/checkout",
            json={"payment_method": "card"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "closed"
        assert data["payment_method"] == "card"
        assert data["amount_subtotal"] == pytest.approx(30.0)
        assert data["tax_amount"] == pytest.approx(6.30, abs=0.01)
        assert data["amount_total"] == pytest.approx(36.30, abs=0.01)
        assert data["closed_at"] is not None

        movs = await auth_client.get(f"/api/v1/products/{product_id}/stock-movements")
        movements = movs.json()
        assert len(movements) == 1
        m = movements[0]
        assert m["movement_type"] == "salida"
        assert m["quantity"] == 3
        assert m["stock_after"] == 7
        assert m["reference"] == f"POS_SESSION:{session_id}"

    @pytest.mark.asyncio
    async def test_checkout_blocks_when_insufficient_stock(
        self, auth_client: AsyncClient
    ):
        product_id = await self._create_product(auth_client, "Prod-E", stock=2)
        sess = await auth_client.post("/api/v1/pos/sessions")
        session_id = sess.json()["id"]
        await auth_client.post(
            f"/api/v1/pos/sessions/{session_id}/lines",
            json={"product_id": product_id, "quantity": 5},
        )

        resp = await auth_client.post(
            f"/api/v1/pos/sessions/{session_id}/checkout",
            json={"payment_method": "cash"},
        )
        assert resp.status_code == 400
        assert "insuficiente" in resp.json()["detail"].lower()

        movs = await auth_client.get(f"/api/v1/products/{product_id}/stock-movements")
        assert movs.json() == []

    @pytest.mark.asyncio
    async def test_checkout_empty_session_blocks(self, auth_client: AsyncClient):
        sess = await auth_client.post("/api/v1/pos/sessions")
        session_id = sess.json()["id"]
        resp = await auth_client.post(
            f"/api/v1/pos/sessions/{session_id}/checkout",
            json={"payment_method": "cash"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cancel_session(self, auth_client: AsyncClient):
        sess = await auth_client.post("/api/v1/pos/sessions")
        session_id = sess.json()["id"]
        resp = await auth_client.post(f"/api/v1/pos/sessions/{session_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cannot_modify_closed_session(self, auth_client: AsyncClient):
        product_id = await self._create_product(auth_client, "Prod-F", stock=10)
        sess = await auth_client.post("/api/v1/pos/sessions")
        session_id = sess.json()["id"]
        await auth_client.post(
            f"/api/v1/pos/sessions/{session_id}/lines",
            json={"product_id": product_id, "quantity": 1},
        )
        await auth_client.post(
            f"/api/v1/pos/sessions/{session_id}/checkout",
            json={"payment_method": "cash"},
        )
        # Una vez cerrada, no se pueden añadir líneas
        resp = await auth_client.post(
            f"/api/v1/pos/sessions/{session_id}/lines",
            json={"product_id": product_id, "quantity": 1},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_session_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.get(f"/api/v1/pos/sessions/{fake_id}")
        assert resp.status_code == 404
