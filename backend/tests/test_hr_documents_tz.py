"""Regresión del DataError naive/aware en hr_documents.

Las columnas created_at/approved_at deben ser timestamptz: el servicio inserta
datetime.now(UTC) (tz-aware). Cuando eran naive, asyncpg rechazaba el INSERT en
Postgres real ("Documento generado pero no guardado") pero SQLite lo aceptaba —
por eso los tests no lo veían. Este test inspecciona el MODELO, así que lo caza
en cualquier BD. Además: un LLM que devuelve un error como contenido (claude_code
en timeout) no debe guardarse como documento.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.db.models.generative_ui import GeneratedUI
from app.db.models.hr_documents import HRDocument


def test_timestamps_son_tz_aware():
    # hr_documents (el bug reportado) y generated_uis (mismo patrón) deben usar
    # timestamptz: el servicio inserta datetime.now(UTC) (aware).
    assert HRDocument.__table__.c.created_at.type.timezone is True, "hr_documents.created_at debe ser timestamptz"
    assert HRDocument.__table__.c.approved_at.type.timezone is True, "hr_documents.approved_at debe ser timestamptz"
    assert GeneratedUI.__table__.c.created_at.type.timezone is True, "generated_uis.created_at debe ser timestamptz"
    assert GeneratedUI.__table__.c.updated_at.type.timezone is True, "generated_uis.updated_at debe ser timestamptz"


@pytest.mark.asyncio
async def test_no_guarda_documento_si_el_llm_devuelve_error(db, seed_tenant_and_user):
    from app.services.hr.commands import generate_document

    tenant, _u, _t = seed_tenant_and_user

    class _FakeLLM:
        async def ainvoke(self, _msgs):
            return SimpleNamespace(
                content="Error: Claude Code CLI no respondió en el tiempo límite."
            )

    with patch("app.services.hr.commands._build_company_context", new=AsyncMock(return_value="")), \
         patch("app.core.llm_factory.get_llm_for_tenant", new=AsyncMock(return_value=_FakeLLM())):
        with pytest.raises(ValueError):
            await generate_document(
                "contract", "un contrato de 40 horas", "Laura Martinez", None, tenant.id, db
            )

    docs = (
        await db.execute(select(HRDocument).where(HRDocument.tenant_id == tenant.id))
    ).scalars().all()
    assert docs == [], "no debe guardar un documento cuyo cuerpo es un error del LLM"
