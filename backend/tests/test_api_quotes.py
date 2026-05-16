"""Tests para endpoints Quotes /api/v1/quotes/*."""
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestQuotesNoAuth:
    @pytest.mark.asyncio
    async def test_list_quotes_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/quotes/")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_quote_no_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/quotes/", json={"client_id": str(uuid4())})
        assert resp.status_code in (401, 403)


class TestQuotes:
    async def _create_client(self, auth_client: AsyncClient) -> str:
        resp = await auth_client.post("/api/v1/clients", json={"name": "Cliente Presupuesto"})
        assert resp.status_code == 201
        return resp.json()["id"]

    @pytest.mark.asyncio
    async def test_list_quotes_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/quotes/")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_quote(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        payload = {
            "client_id": client_id,
            "status": "draft",
            "lines": [
                {
                    "description": "Servicio de diseño",
                    "quantity": 1.0,
                    "unit_price": 500.0,
                    "tax_percentage": 21.0,
                }
            ],
        }
        resp = await auth_client.post("/api/v1/quotes/", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["client_id"] == client_id
        assert data["status"] == "draft"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_quote_no_lines(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        payload = {"client_id": client_id}
        resp = await auth_client.post("/api/v1/quotes/", json=payload)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_quote_missing_client_id(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/quotes/", json={"status": "draft"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_quote(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        create_resp = await auth_client.post(
            "/api/v1/quotes/", json={"client_id": client_id}
        )
        quote_id = create_resp.json()["id"]
        resp = await auth_client.get(f"/api/v1/quotes/{quote_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == quote_id

    @pytest.mark.asyncio
    async def test_get_quote_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.get(f"/api/v1/quotes/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_quote(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        create_resp = await auth_client.post(
            "/api/v1/quotes/", json={"client_id": client_id}
        )
        quote_id = create_resp.json()["id"]
        resp = await auth_client.patch(
            f"/api/v1/quotes/{quote_id}", json={"notes": "Updated notes", "status": "sent"}
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Updated notes"

    @pytest.mark.asyncio
    async def test_update_quote_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.patch(
            f"/api/v1/quotes/{fake_id}", json={"notes": "X"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_quote(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        create_resp = await auth_client.post(
            "/api/v1/quotes/", json={"client_id": client_id}
        )
        quote_id = create_resp.json()["id"]
        resp = await auth_client.delete(f"/api/v1/quotes/{quote_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_quote_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.delete(f"/api/v1/quotes/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_quotes_after_create(self, auth_client: AsyncClient):
        client_id = await self._create_client(auth_client)
        await auth_client.post("/api/v1/quotes/", json={"client_id": client_id})
        await auth_client.post("/api/v1/quotes/", json={"client_id": client_id})
        resp = await auth_client.get("/api/v1/quotes/")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
