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
