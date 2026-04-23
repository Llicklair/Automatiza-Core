"""Tests para endpoints Sales Orders /api/v1/orders/*."""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from tests.conftest import _TestSessionLocal


class TestSalesOrders:
    @pytest.mark.asyncio
    async def test_list_sales_orders_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/orders")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_sales_order(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from app.db.models.models import Client
        async with _TestSessionLocal() as db:
            client_record = Client(tenant_id=tenant.id, name="Cliente Venta", nif="B11111111")
            db.add(client_record)
            await db.commit()
            await db.refresh(client_record)
            client_id = str(client_record.id)

        payload = {
            "client_id": client_id,
            "notes": "Pedido de prueba",
            "lines": [
                {
                    "description": "Servicio consultoria",
                    "quantity": 2.0,
                    "unit_price": 100.0,
                    "tax_percentage": 21.0,
                }
            ],
        }
        resp = await auth_client.post("/api/v1/orders", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["notes"] == "Pedido de prueba"

    @pytest.mark.asyncio
    async def test_create_sales_order_no_lines(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from app.db.models.models import Client
        async with _TestSessionLocal() as db:
            client_record = Client(tenant_id=tenant.id, name="Cliente Sin Lineas", nif="B22222222")
            db.add(client_record)
            await db.commit()
            await db.refresh(client_record)
            client_id = str(client_record.id)

        payload = {"client_id": client_id}
        resp = await auth_client.post("/api/v1/orders", json=payload)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_sales_order_missing_client_id(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/orders", json={"notes": "sin client_id"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_sales_order(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from app.db.models.models import Client
        async with _TestSessionLocal() as db:
            client_record = Client(tenant_id=tenant.id, name="Cliente Update", nif="B33333333")
            db.add(client_record)
            await db.commit()
            await db.refresh(client_record)
            client_id = str(client_record.id)

        create_resp = await auth_client.post("/api/v1/orders", json={
            "client_id": client_id,
            "lines": [{"description": "Item", "quantity": 1, "unit_price": 50}],
        })
        assert create_resp.status_code == 201
        order_id = create_resp.json()["id"]

        resp = await auth_client.patch(f"/api/v1/orders/{order_id}", json={
            "notes": "Actualizado",
        })
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Actualizado"

    @pytest.mark.asyncio
    async def test_update_sales_order_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.patch(f"/api/v1/orders/{fake_id}", json={"notes": "x"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_sales_order(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from app.db.models.models import Client
        async with _TestSessionLocal() as db:
            client_record = Client(tenant_id=tenant.id, name="Cliente Delete", nif="B44444444")
            db.add(client_record)
            await db.commit()
            await db.refresh(client_record)
            client_id = str(client_record.id)

        create_resp = await auth_client.post("/api/v1/orders", json={
            "client_id": client_id,
        })
        order_id = create_resp.json()["id"]

        resp = await auth_client.delete(f"/api/v1/orders/{order_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_sales_order_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.delete(f"/api/v1/orders/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_sales_orders_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/orders")
        assert resp.status_code in (401, 403)
