"""Tests para el PDF server-side de documentos de gestoría (2.9 — base de firma)."""
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHRDocumentPdf:
    async def test_pdf_unknown_returns_404(self, auth_client: AsyncClient):
        resp = await auth_client.get(f"/api/v1/hr/documents/{uuid4()}/pdf")
        assert resp.status_code == 404

    async def test_pdf_renders_bytes(self, db, auth_client, seed_tenant_and_user):
        pytest.importorskip("xhtml2pdf")  # dependencia declarada; puede faltar en dev
        from app.db.models.hr_documents import HRDocument

        tenant, _u, _t = seed_tenant_and_user
        doc = HRDocument(
            id=uuid4(), tenant_id=tenant.id, doc_type="contract",
            title="Contrato Test",
            content_html="<h1>Contrato de Trabajo</h1><p>Cuerpo del contrato.</p>",
            status="approved", doc_number="DOC-2026-0001",
        )
        db.add(doc)
        await db.commit()

        resp = await auth_client.get(f"/api/v1/hr/documents/{doc.id}/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content[:4] == b"%PDF"
        assert "DOC-2026-0001.pdf" in resp.headers.get("content-disposition", "")
