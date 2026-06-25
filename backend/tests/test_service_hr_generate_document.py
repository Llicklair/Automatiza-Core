"""Regresión R2 (2026-06-25): `generate_document` persiste el HRDocument con el `db`
inyectado de la request, no con una `AsyncSessionLocal` aparte (transacción paralela).

Mockea solo el LLM; ejercita el guardado real (antes cubierto por un test que mockeaba
la función entera).
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy import select

from app.db.models.hr_documents import HRDocument
from app.services.hr.commands import generate_document


@pytest.mark.asyncio
async def test_generate_document_persiste_con_db_inyectado(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="<p>Contrato de prueba</p>"))

    with patch(
        "app.core.llm_factory.get_llm_for_tenant",
        new=AsyncMock(return_value=mock_llm),
    ):
        result = await generate_document(
            doc_type="contrato",
            instructions="Contrato indefinido",
            employee_name="Ana",
            employee_id=None,
            tenant_id=tenant.id,
            db=db,
        )

    # El dict devuelto trae los campos recargados (prueba de que refresh funcionó).
    assert result["status"] == "draft"
    assert result["title"]
    assert result["content_html"] == "<p>Contrato de prueba</p>"
    assert result["created_at"]

    # El HRDocument es visible en la MISMA sesión `db` (se guardó con el db inyectado,
    # no en una sesión paralela) y sin disparar lazy-load.
    row = (
        await db.execute(select(HRDocument).where(HRDocument.id == UUID(result["id"])))
    ).scalar_one_or_none()
    assert row is not None
    assert row.tenant_id == tenant.id
    assert row.status == "draft"
