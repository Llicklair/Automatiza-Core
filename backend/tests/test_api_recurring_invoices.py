"""Tests para endpoints Recurring Invoices /api/v1/recurring-invoices/*."""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from tests.conftest import _TestSessionLocal


class TestRecurringInvoices:
    @pytest.mark.asyncio
    async def test_list_recurring_invoices_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/recurring-invoices")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_recurring_invoice(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from app.db.models.models import Client
        async with _TestSessionLocal() as db:
            client_record = Client(tenant_id=tenant.id, name="Cliente Recurrente", nif="B99999999")
            db.add(client_record)
            await db.commit()
            await db.refresh(client_record)
            client_id = str(client_record.id)

        payload = {
            "client_id": client_id,
            "name": "Cuota mensual mantenimiento",
            "interval_type": "monthly",
            "next_run_date": "2026-05-01",
            "lines": [
                {
                    "description": "Mantenimiento servidor",
                    "quantity": 1.0,
                    "unit_price": 200.0,
                    "tax_percentage": 21.0,
                }
            ],
        }
        resp = await auth_client.post("/api/v1/recurring-invoices", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == "Cuota mensual mantenimiento"
        assert data["interval_type"] == "monthly"

    @pytest.mark.asyncio
    async def test_create_recurring_invoice_minimal(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from app.db.models.models import Client
        async with _TestSessionLocal() as db:
            client_record = Client(tenant_id=tenant.id, name="Cliente Min", nif="A11111111")
            db.add(client_record)
            await db.commit()
            await db.refresh(client_record)
            client_id = str(client_record.id)

        payload = {
            "client_id": client_id,
            "name": "Recurrente minimo",
            "next_run_date": "2026-06-01",
        }
        resp = await auth_client.post("/api/v1/recurring-invoices", json=payload)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_recurring_invoice_missing_name(self, auth_client: AsyncClient):
        fake_client = str(uuid4())
        resp = await auth_client.post("/api/v1/recurring-invoices", json={
            "client_id": fake_client,
            "next_run_date": "2026-05-01",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_recurring_invoice_missing_date(self, auth_client: AsyncClient):
        fake_client = str(uuid4())
        resp = await auth_client.post("/api/v1/recurring-invoices", json={
            "client_id": fake_client,
            "name": "Sin fecha",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_recurring_invoice(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from app.db.models.models import Client
        async with _TestSessionLocal() as db:
            client_record = Client(tenant_id=tenant.id, name="Cliente Update Rec", nif="A22222222")
            db.add(client_record)
            await db.commit()
            await db.refresh(client_record)
            client_id = str(client_record.id)

        create_resp = await auth_client.post("/api/v1/recurring-invoices", json={
            "client_id": client_id,
            "name": "Recurrente Update",
            "next_run_date": "2026-07-01",
        })
        assert create_resp.status_code == 201
        rec_id = create_resp.json()["id"]

        resp = await auth_client.patch(f"/api/v1/recurring-invoices/{rec_id}", json={
            "name": "Recurrente Actualizado",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Recurrente Actualizado"

    @pytest.mark.asyncio
    async def test_update_recurring_invoice_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.patch(f"/api/v1/recurring-invoices/{fake_id}", json={
            "name": "No existe",
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_recurring_invoice(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from app.db.models.models import Client
        async with _TestSessionLocal() as db:
            client_record = Client(tenant_id=tenant.id, name="Cliente Delete Rec", nif="A33333333")
            db.add(client_record)
            await db.commit()
            await db.refresh(client_record)
            client_id = str(client_record.id)

        create_resp = await auth_client.post("/api/v1/recurring-invoices", json={
            "client_id": client_id,
            "name": "Recurrente Delete",
            "next_run_date": "2026-08-01",
        })
        rec_id = create_resp.json()["id"]

        resp = await auth_client.delete(f"/api/v1/recurring-invoices/{rec_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_recurring_invoice_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.delete(f"/api/v1/recurring-invoices/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_recurring_invoices_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/recurring-invoices")
        assert resp.status_code in (401, 403)
