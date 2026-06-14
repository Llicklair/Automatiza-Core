"""Tests para el endpoint de búsqueda semántica GET /api/v1/documents/search."""
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


class _FakeEmbedder:
    """Embedder de prueba — evita cargar el modelo HuggingFace real (~570MB)."""

    async def aembed_query(self, text):  # noqa: ARG002
        return [1.0, 0.0, 0.0]


@pytest.mark.asyncio
class TestDocumentsSearch:
    async def test_empty_query_returns_400(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/documents/search", params={"q": "   "})
        assert resp.status_code == 400

    async def test_no_embedder_returns_503(self, auth_client: AsyncClient):
        with patch("app.core.llm_factory.get_embedder", return_value=None):
            resp = await auth_client.get(
                "/api/v1/documents/search", params={"q": "factura"}
            )
        assert resp.status_code == 503

    async def test_returns_ranked_hits(self, db, auth_client, seed_tenant_and_user):
        from app.db.models.embeddings import DocumentEmbedding

        tenant, _user, _token = seed_tenant_and_user
        db.add_all(
            [
                DocumentEmbedding(
                    id=uuid4(), document_id=uuid4(), tenant_id=tenant.id,
                    chunk_index="0", text_content="contrato cercano",
                    embedding=[0.9, 0.1, 0.0],
                ),
                DocumentEmbedding(
                    id=uuid4(), document_id=uuid4(), tenant_id=tenant.id,
                    chunk_index="0", text_content="lejano",
                    embedding=[-1.0, 0.0, 0.0],
                ),
            ]
        )
        await db.commit()

        with patch("app.core.llm_factory.get_embedder", return_value=_FakeEmbedder()):
            resp = await auth_client.get(
                "/api/v1/documents/search", params={"q": "contrato", "limit": 1}
            )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["text"] == "contrato cercano"
        assert body[0]["similarity"] > 0.9

    async def test_filters_by_tenant(
        self, db, auth_client, seed_tenant_and_user, seed_second_tenant_and_user
    ):
        from app.db.models.embeddings import DocumentEmbedding

        _tenant_a, _ua, _ta = seed_tenant_and_user
        tenant_b, _ub, _tb = seed_second_tenant_and_user
        # Embedding solo del tenant B — el auth_client (tenant A) no debe verlo.
        db.add(
            DocumentEmbedding(
                id=uuid4(), document_id=uuid4(), tenant_id=tenant_b.id,
                chunk_index="0", text_content="documento ajeno",
                embedding=[1.0, 0.0, 0.0],
            )
        )
        await db.commit()

        with patch("app.core.llm_factory.get_embedder", return_value=_FakeEmbedder()):
            resp = await auth_client.get(
                "/api/v1/documents/search", params={"q": "documento"}
            )
        assert resp.status_code == 200
        assert resp.json() == []
