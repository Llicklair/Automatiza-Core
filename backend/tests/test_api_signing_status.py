"""Test del endpoint de estado de firma AutoFirma (F3.11 — polling)."""
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestSigningStatus:
    async def test_unknown_session_returns_404(self, auth_client: AsyncClient):
        resp = await auth_client.get(f"/api/v1/signing/autofirma/status/{uuid4().hex}")
        assert resp.status_code == 404

    async def test_returns_status(self, db, auth_client, seed_tenant_and_user):
        from app.db.models.signed_document import SignedDocument

        tenant, _u, _t = seed_tenant_and_user
        sd = SignedDocument(
            id=uuid4(), tenant_id=tenant.id, session_token="tok-abc123",
            signature_format="PAdES", status="pending", original_hash="h" * 64,
        )
        db.add(sd)
        await db.commit()

        resp = await auth_client.get("/api/v1/signing/autofirma/status/tok-abc123")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_token"] == "tok-abc123"
        assert body["status"] == "pending"

    async def test_status_scoped_by_tenant(
        self, db, auth_client, seed_tenant_and_user, seed_second_tenant_and_user
    ):
        from app.db.models.signed_document import SignedDocument

        _tenant_a, _ua, _ta = seed_tenant_and_user
        tenant_b, _ub, _tb = seed_second_tenant_and_user
        # Sesión del tenant B — el auth_client (tenant A) no debe verla.
        db.add(SignedDocument(
            id=uuid4(), tenant_id=tenant_b.id, session_token="tok-ajeno",
            signature_format="PAdES", status="signed", original_hash="x" * 64,
        ))
        await db.commit()

        resp = await auth_client.get("/api/v1/signing/autofirma/status/tok-ajeno")
        assert resp.status_code == 404
