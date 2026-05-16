"""Tests para endpoints Products /api/v1/products/*."""
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestProductsNoAuth:
    @pytest.mark.asyncio
    async def test_list_products_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/products")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_product_no_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/products", json={"name": "Test"})
        assert resp.status_code in (401, 403)


class TestProducts:
    @pytest.mark.asyncio
    async def test_list_products_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/products")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_product(self, auth_client: AsyncClient):
        payload = {
            "name": "Widget Premium",
            "item_type": "product",
            "sku": "WDG-001",
            "description": "Widget de alta calidad",
            "price": 49.99,
            "tax_percentage": 21.0,
            "stock_quantity": 100,
            "stock_min_alert": 10,
        }
        resp = await auth_client.post("/api/v1/products", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Widget Premium"
        assert data["price"] == 49.99
        assert data["sku"] == "WDG-001"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_product_minimal(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/products", json={"name": "Simple"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Simple"
        assert data["price"] == 0.0

    @pytest.mark.asyncio
    async def test_create_product_missing_name(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/products", json={"price": 10.0})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_service(self, auth_client: AsyncClient):
        payload = {"name": "Consultoría", "item_type": "service", "price": 150.0}
        resp = await auth_client.post("/api/v1/products", json=payload)
        assert resp.status_code == 201
        assert resp.json()["item_type"] == "service"

    @pytest.mark.asyncio
    async def test_list_products_after_create(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/products", json={"name": "Prod1"})
        await auth_client.post("/api/v1/products", json={"name": "Prod2"})
        resp = await auth_client.get("/api/v1/products")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_update_product(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/v1/products", json={"name": "Original", "price": 10.0})
        product_id = create_resp.json()["id"]
        resp = await auth_client.patch(
            f"/api/v1/products/{product_id}", json={"name": "Actualizado", "price": 25.0}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Actualizado"
        assert resp.json()["price"] == 25.0

    @pytest.mark.asyncio
    async def test_update_product_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.patch(f"/api/v1/products/{fake_id}", json={"name": "X"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_product(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/v1/products", json={"name": "A Borrar"})
        product_id = create_resp.json()["id"]
        resp = await auth_client.delete(f"/api/v1/products/{product_id}")
        assert resp.status_code == 204
        # Verify deleted
        list_resp = await auth_client.get("/api/v1/products")
        assert len(list_resp.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_product_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.delete(f"/api/v1/products/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_products_pagination(self, auth_client: AsyncClient):
        for i in range(5):
            await auth_client.post("/api/v1/products", json={"name": f"Prod{i}"})
        resp = await auth_client.get("/api/v1/products?skip=0&limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestStockValuation:
    @pytest.mark.asyncio
    async def test_valuation_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/stock/valuation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_value"] == 0
        assert data["total_units"] == 0
        assert data["product_count"] == 0
        assert data["by_category"] == []

    @pytest.mark.asyncio
    async def test_valuation_sums_quantity_times_cost(self, auth_client: AsyncClient):
        await auth_client.post(
            "/api/v1/products",
            json={"name": "Tornillo", "category": "ferreteria", "stock_quantity": 100, "cost_price": 0.5, "price": 1.0},
        )
        await auth_client.post(
            "/api/v1/products",
            json={"name": "Tuerca", "category": "ferreteria", "stock_quantity": 50, "cost_price": 0.2, "price": 0.5},
        )
        await auth_client.post(
            "/api/v1/products",
            json={"name": "Aceite", "category": "lubricantes", "stock_quantity": 10, "cost_price": 8.0, "price": 15.0},
        )

        resp = await auth_client.get("/api/v1/stock/valuation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_units"] == 160
        assert data["total_value"] == pytest.approx(100 * 0.5 + 50 * 0.2 + 10 * 8.0)
        assert data["product_count"] == 3
        assert data["missing_cost_price_count"] == 0
        cats = {c["category"]: c for c in data["by_category"]}
        assert cats["ferreteria"]["units"] == 150
        assert cats["ferreteria"]["value"] == pytest.approx(60.0)
        assert cats["lubricantes"]["units"] == 10
        assert cats["lubricantes"]["value"] == pytest.approx(80.0)

    @pytest.mark.asyncio
    async def test_valuation_flags_missing_cost_price(self, auth_client: AsyncClient):
        await auth_client.post(
            "/api/v1/products",
            json={"name": "Sin coste", "stock_quantity": 20},
        )
        resp = await auth_client.get("/api/v1/stock/valuation")
        data = resp.json()
        assert data["missing_cost_price_count"] == 1
        assert data["total_value"] == 0
        assert data["total_units"] == 20

    @pytest.mark.asyncio
    async def test_valuation_excludes_inactive(self, auth_client: AsyncClient):
        await auth_client.post(
            "/api/v1/products",
            json={"name": "Activo", "stock_quantity": 5, "cost_price": 10.0},
        )
        create_resp = await auth_client.post(
            "/api/v1/products",
            json={"name": "Inactivo", "stock_quantity": 100, "cost_price": 99.0},
        )
        inactive_id = create_resp.json()["id"]
        await auth_client.patch(f"/api/v1/products/{inactive_id}", json={"is_active": False})

        resp = await auth_client.get("/api/v1/stock/valuation")
        data = resp.json()
        assert data["product_count"] == 1
        assert data["total_units"] == 5
        assert data["total_value"] == pytest.approx(50.0)
