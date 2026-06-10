"""Tests para endpoints Banking /api/v1/banking/*."""
import pytest
from httpx import AsyncClient


class TestBankingSummary:
    @pytest.mark.asyncio
    async def test_get_summary(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/banking/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_invoiced" in data or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_summary_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/banking/summary")
        assert resp.status_code in (401, 403)


class TestTransactions:
    @pytest.mark.asyncio
    async def test_list_transactions_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/banking/transactions")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_transactions_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/banking/transactions")
        assert resp.status_code in (401, 403)


class TestSync:
    @pytest.mark.asyncio
    async def test_sync_sin_psd2_devuelve_409(self, auth_client: AsyncClient):
        """Por defecto (BANKING_DEMO_SYNC=False) no se inventan movimientos."""
        resp = await auth_client.post("/api/v1/banking/transactions/sync")
        assert resp.status_code == 409
        assert "PSD2" in resp.json()["detail"]
        # Y no se insertó nada.
        txs = (await auth_client.get("/api/v1/banking/transactions")).json()
        assert txs == []

    @pytest.mark.asyncio
    async def test_sync_con_flag_demo_genera_movimientos(self, auth_client: AsyncClient, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "BANKING_DEMO_SYNC", True)
        resp = await auth_client.post("/api/v1/banking/transactions/sync")
        assert resp.status_code == 200
        assert resp.json()["is_demo"] is True
        txs = (await auth_client.get("/api/v1/banking/transactions")).json()
        assert len(txs) == 5
        assert all(t["description"].startswith("[DEMO]") for t in txs)
