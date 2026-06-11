"""Tests del asistente conversacional de contratos (Feature 3)."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.documents.contracts_interview import run_interview


class _FakeLLM:
    def __init__(self, content: str):
        self._content = content

    async def ainvoke(self, _messages):
        class _R:
            content = self._content

        _R.content = self._content
        return _R()


@pytest.mark.asyncio
class TestContractsInterview:
    async def test_returns_question_when_not_done(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        fake = AsyncMock(return_value=_FakeLLM("¿Cuál es el NIF de la empresa contratante?"))
        with patch("app.core.llm_factory.get_llm_for_tenant", new=fake):
            res = await run_interview(tenant.id, db, "servicios", [])
        assert res["done"] is False
        assert "NIF" in res["message"]
        assert res["contract"] is None

    async def test_extracts_final_contract(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        content = (
            "Con estos datos ya puedo redactarlo.\n"
            "=== CONTRATO FINALIZADO ===\n"
            "# Contrato de Prestación de Servicios\nCuerpo real del contrato."
        )
        fake = AsyncMock(return_value=_FakeLLM(content))
        with patch("app.core.llm_factory.get_llm_for_tenant", new=fake):
            res = await run_interview(
                tenant.id, db, "servicios", [{"role": "user", "content": "ACME, B123..."}]
            )
        assert res["done"] is True
        assert res["contract"].startswith("# Contrato de Prestación de Servicios")
        assert "FINALIZADO" not in res["contract"]

    async def test_invalid_type_raises(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises(ValueError):
            await run_interview(tenant.id, db, "inexistente", [])

    async def test_endpoint_invalid_type_422(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/documents/contracts/interview",
            json={"contract_type": "inexistente", "messages": []},
        )
        assert resp.status_code == 422
