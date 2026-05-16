"""Tests para endpoints Approvals /api/v1/approvals/*."""
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestApprovals:
    @pytest.mark.asyncio
    async def test_list_pending_approvals_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/approvals")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_decide_approval_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.post(f"/api/v1/approvals/{fake_id}/decide", json={
            "approved": True,
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_decide_approval_reject_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.post(f"/api/v1/approvals/{fake_id}/decide", json={
            "approved": False,
            "rejection_reason": "No procede",
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_decide_approval_missing_approved_field(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.post(f"/api/v1/approvals/{fake_id}/decide", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_cleanup_approvals_empty(self, auth_client: AsyncClient):
        resp = await auth_client.delete("/api/v1/approvals/cleanup")
        assert resp.status_code == 200
        data = resp.json()
        assert "deleted" in data
        assert data["deleted"] == 0

    @pytest.mark.asyncio
    async def test_approvals_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/approvals")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_cleanup_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/api/v1/approvals/cleanup")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_decide_requires_auth(self, client: AsyncClient):
        fake_id = str(uuid4())
        resp = await client.post(f"/api/v1/approvals/{fake_id}/decide", json={
            "approved": True,
        })
        assert resp.status_code in (401, 403)
