"""Tests para endpoints Accounting /api/v1/accounting/*."""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime


class TestAccountingNoAuth:
    @pytest.mark.asyncio
    async def test_list_journal_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/accounting/journal")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_assets_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/accounting/assets")
        assert resp.status_code in (401, 403)


class TestJournalEntries:
    @pytest.mark.asyncio
    async def test_list_journal_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/accounting/journal")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_journal_entry(self, auth_client: AsyncClient):
        payload = {
            "date": datetime.now().isoformat(),
            "description": "Asiento de apertura",
            "lines": [
                {"account_code": "570", "account_name": "Caja", "debit": 1000.0, "credit": 0.0},
                {"account_code": "100", "account_name": "Capital", "debit": 0.0, "credit": 1000.0},
            ],
        }
        resp = await auth_client.post("/api/v1/accounting/journal", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["description"] == "Asiento de apertura"
        assert len(data["lines"]) == 2
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_journal_entry_missing_description(self, auth_client: AsyncClient):
        payload = {
            "date": datetime.now().isoformat(),
            "lines": [
                {"account_code": "570", "debit": 100.0, "credit": 0.0},
            ],
        }
        resp = await auth_client.post("/api/v1/accounting/journal", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_journal_entry_missing_lines(self, auth_client: AsyncClient):
        payload = {
            "date": datetime.now().isoformat(),
            "description": "Sin lineas",
        }
        resp = await auth_client.post("/api/v1/accounting/journal", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_journal_entry_unbalanced(self, auth_client: AsyncClient):
        payload = {
            "date": datetime.now().isoformat(),
            "description": "Descuadrado",
            "lines": [
                {"account_code": "570", "debit": 1000.0, "credit": 0.0},
                {"account_code": "100", "debit": 0.0, "credit": 500.0},
            ],
        }
        resp = await auth_client.post("/api/v1/accounting/journal", json=payload)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_journal_entry(self, auth_client: AsyncClient):
        payload = {
            "date": datetime.now().isoformat(),
            "description": "A borrar",
            "lines": [
                {"account_code": "570", "debit": 100.0, "credit": 0.0},
                {"account_code": "100", "debit": 0.0, "credit": 100.0},
            ],
        }
        create_resp = await auth_client.post("/api/v1/accounting/journal", json=payload)
        entry_id = create_resp.json()["id"]
        resp = await auth_client.delete(f"/api/v1/accounting/journal/{entry_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_journal_entry_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.delete(f"/api/v1/accounting/journal/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_journal_after_create(self, auth_client: AsyncClient):
        payload = {
            "date": datetime.now().isoformat(),
            "description": "Asiento test",
            "lines": [
                {"account_code": "570", "debit": 200.0, "credit": 0.0},
                {"account_code": "100", "debit": 0.0, "credit": 200.0},
            ],
        }
        await auth_client.post("/api/v1/accounting/journal", json=payload)
        resp = await auth_client.get("/api/v1/accounting/journal")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestFixedAssets:
    @pytest.mark.asyncio
    async def test_list_assets_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/accounting/assets")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_fixed_asset(self, auth_client: AsyncClient):
        payload = {
            "name": "Ordenador Dell",
            "category": "Equipos informáticos",
            "purchase_date": "2024-01-15",
            "purchase_value": 1200.0,
            "useful_life_years": 4.0,
            "residual_value": 100.0,
        }
        resp = await auth_client.post("/api/v1/accounting/assets", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Ordenador Dell"
        assert data["purchase_value"] == 1200.0
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_fixed_asset_minimal(self, auth_client: AsyncClient):
        payload = {
            "name": "Silla oficina",
            "purchase_date": "2024-06-01",
            "purchase_value": 300.0,
        }
        resp = await auth_client.post("/api/v1/accounting/assets", json=payload)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_fixed_asset_missing_name(self, auth_client: AsyncClient):
        payload = {
            "purchase_date": "2024-01-01",
            "purchase_value": 500.0,
        }
        resp = await auth_client.post("/api/v1/accounting/assets", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_fixed_asset_missing_purchase_date(self, auth_client: AsyncClient):
        payload = {
            "name": "Impresora",
            "purchase_value": 500.0,
        }
        resp = await auth_client.post("/api/v1/accounting/assets", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_fixed_asset(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            "/api/v1/accounting/assets",
            json={"name": "Original", "purchase_date": "2024-01-01", "purchase_value": 1000.0},
        )
        asset_id = create_resp.json()["id"]
        resp = await auth_client.patch(
            f"/api/v1/accounting/assets/{asset_id}",
            json={"name": "Actualizado", "category": "Mobiliario"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Actualizado"
        assert resp.json()["category"] == "Mobiliario"

    @pytest.mark.asyncio
    async def test_update_fixed_asset_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.patch(
            f"/api/v1/accounting/assets/{fake_id}", json={"name": "X"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_fixed_asset(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            "/api/v1/accounting/assets",
            json={"name": "A Borrar", "purchase_date": "2024-01-01", "purchase_value": 500.0},
        )
        asset_id = create_resp.json()["id"]
        resp = await auth_client.delete(f"/api/v1/accounting/assets/{asset_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_fixed_asset_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.delete(f"/api/v1/accounting/assets/{fake_id}")
        assert resp.status_code == 404
