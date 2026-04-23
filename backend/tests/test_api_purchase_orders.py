"""Tests para endpoints Purchase Orders /api/v1/purchase-orders/*."""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from tests.conftest import _TestSessionLocal


class TestPurchaseOrders:
    @pytest.mark.asyncio
    async def test_list_purchase_orders_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/purchase-orders")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_purchase_order(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        # PurchaseOrder requires supplier_id — create a Client as supplier stand-in
        # The supplier_id is a UUID FK; we create a Client record since models often reuse Client
        from app.db.models.models import Client
        async with _TestSessionLocal() as db:
            supplier = Client(tenant_id=tenant.id, name="Proveedor Test", nif="B55555555")
            db.add(supplier)
            await db.commit()
            await db.refresh(supplier)
            supplier_id = str(supplier.id)

        payload = {
            "supplier_id": supplier_id,
            "notes": "Pedido de compra test",
            "lines": [
                {
                    "description": "Materia prima",
                    "quantity": 10.0,
                    "unit_price": 25.0,
                    "tax_percentage": 21.0,
                }
            ],
        }
        resp = await auth_client.post("/api/v1/purchase-orders", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_purchase_order_no_lines(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from app.db.models.models import Client
        async with _TestSessionLocal() as db:
            supplier = Client(tenant_id=tenant.id, name="Proveedor Vacio", nif="B66666666")
            db.add(supplier)
            await db.commit()
            await db.refresh(supplier)
            supplier_id = str(supplier.id)

        payload = {"supplier_id": supplier_id}
        resp = await auth_client.post("/api/v1/purchase-orders", json=payload)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_purchase_order_missing_supplier(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/purchase-orders", json={"notes": "sin supplier"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_purchase_order(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from app.db.models.models import Client
        async with _TestSessionLocal() as db:
            supplier = Client(tenant_id=tenant.id, name="Proveedor Update", nif="B77777777")
            db.add(supplier)
            await db.commit()
            await db.refresh(supplier)
            supplier_id = str(supplier.id)

        create_resp = await auth_client.post("/api/v1/purchase-orders", json={
            "supplier_id": supplier_id,
            "lines": [{"description": "Item", "quantity": 1, "unit_price": 30}],
        })
        assert create_resp.status_code == 201
        order_id = create_resp.json()["id"]

        resp = await auth_client.patch(f"/api/v1/purchase-orders/{order_id}", json={
            "notes": "Actualizado compra",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_purchase_order_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.patch(f"/api/v1/purchase-orders/{fake_id}", json={"notes": "x"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_purchase_order(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from app.db.models.models import Client
        async with _TestSessionLocal() as db:
            supplier = Client(tenant_id=tenant.id, name="Proveedor Delete", nif="B88888888")
            db.add(supplier)
            await db.commit()
            await db.refresh(supplier)
            supplier_id = str(supplier.id)

        create_resp = await auth_client.post("/api/v1/purchase-orders", json={
            "supplier_id": supplier_id,
        })
        order_id = create_resp.json()["id"]

        resp = await auth_client.delete(f"/api/v1/purchase-orders/{order_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_purchase_order_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.delete(f"/api/v1/purchase-orders/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_purchase_orders_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/purchase-orders")
        assert resp.status_code in (401, 403)
