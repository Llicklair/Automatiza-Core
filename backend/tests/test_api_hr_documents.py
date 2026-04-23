"""Tests para endpoints HR Documents /api/v1/hr/documents/*."""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import AsyncMock, patch


class TestHRDocuments:
    @pytest.mark.asyncio
    async def test_list_hr_documents_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/hr/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_generate_hr_document(self, auth_client: AsyncClient):
        """Generate endpoint calls LLM — we mock the service to avoid external calls."""
        mock_result = {
            "id": str(uuid4()),
            "doc_type": "contract",
            "title": "Contrato de trabajo - Juan",
            "employee_name": "Juan Garcia",
            "content_html": "<p>Contrato de prueba</p>",
            "status": "draft",
            "instructions": "Contrato indefinido",
            "created_at": "2026-04-23T10:00:00",
            "approved_at": None,
        }
        with patch("app.services.hr.documents.generate_document", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_result
            payload = {
                "doc_type": "contract",
                "instructions": "Contrato indefinido para desarrollador",
                "employee_name": "Juan Garcia",
            }
            resp = await auth_client.post("/api/v1/hr/documents/generate", json=payload)
            assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_generate_hr_document_missing_doc_type(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/hr/documents/generate", json={
            "instructions": "Algo",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_hr_document_minimal(self, auth_client: AsyncClient):
        """Only doc_type is required."""
        mock_result = {
            "id": str(uuid4()),
            "doc_type": "nda",
            "title": "NDA",
            "employee_name": None,
            "content_html": "<p>NDA</p>",
            "status": "draft",
            "instructions": "",
            "created_at": "2026-04-23T10:00:00",
            "approved_at": None,
        }
        with patch("app.services.hr.documents.generate_document", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_result
            resp = await auth_client.post("/api/v1/hr/documents/generate", json={
                "doc_type": "nda",
            })
            assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_get_hr_document_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.get(f"/api/v1/hr/documents/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_hr_document_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.post(f"/api/v1/hr/documents/{fake_id}/approve")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_hr_document_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.delete(f"/api/v1/hr/documents/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_hr_documents_with_filters(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/hr/documents?doc_type=contract&status=draft&limit=10&offset=0")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_hr_documents_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/hr/documents")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_generate_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/hr/documents/generate", json={
            "doc_type": "contract",
        })
        assert resp.status_code in (401, 403)
