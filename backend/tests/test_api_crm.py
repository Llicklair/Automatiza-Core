"""Tests para endpoints CRM /api/v1/crm/*."""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestOpportunities:
    @pytest.mark.asyncio
    async def test_list_opportunities_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/crm/opportunities")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_opportunity(self, auth_client: AsyncClient, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        from app.db.models.models import Client
        from tests.conftest import _TestSessionLocal
        async with _TestSessionLocal() as db:
            client_record = Client(tenant_id=tenant.id, name="Cliente Test", nif="B99999999")
            db.add(client_record)
            await db.commit()
            await db.refresh(client_record)
            client_id = client_record.id

        payload = {
            "client_id": str(client_id),
            "title": "Oportunidad venta software",
            "expected_value": 15000.0,
            "stage": "new",
        }
        resp = await auth_client.post("/api/v1/crm/opportunities", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Oportunidad venta software"
        assert data["expected_value"] == 15000.0
        assert data["stage"] == "new"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_opportunity_missing_title(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/crm/opportunities", json={
            "client_id": str(uuid4()),
            "expected_value": 1000.0,
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_opportunities_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/crm/opportunities")
        assert resp.status_code in (401, 403)


class TestActivities:
    @pytest.mark.asyncio
    async def test_list_activities_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/crm/activities")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_activity(self, auth_client: AsyncClient):
        payload = {"type": "call", "description": "Llamada de seguimiento"}
        resp = await auth_client.post("/api/v1/crm/activities", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "call"
        assert data["description"] == "Llamada de seguimiento"


class TestEvents:
    @pytest.mark.asyncio
    async def test_list_events_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/crm/events")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_event(self, auth_client: AsyncClient):
        payload = {
            "title": "Reunion comercial",
            "start_time": "2026-04-10T10:00:00",
            "end_time": "2026-04-10T11:00:00",
            "type": "meeting",
        }
        resp = await auth_client.post("/api/v1/crm/events", json=payload)
        assert resp.status_code == 201
        assert resp.json()["title"] == "Reunion comercial"
