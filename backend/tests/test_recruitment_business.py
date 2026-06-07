"""Tests de negocio del agente recruitment.

A diferencia de test_recruitment_agent.py (smoke: grafo y registro de tools),
estos tests ejercitan la LÓGICA real de las tools: validación de entrada y
degradación con gracia ante fallos (UUID inválido, CV ilegible, LLM caído).
No requieren BD: cubren las ramas que retornan antes de tocar PostgreSQL.
"""
from unittest.mock import patch

import pytest

from app.agents.recruitment.tools import (
    create_candidate,
    create_position,
    list_candidates,
    list_positions,
    process_cv,
    update_candidate_status,
)

VALID_TENANT = "00000000-0000-0000-0000-000000000001"
VALID_POS = "00000000-0000-0000-0000-0000000000aa"


# ── Validación de entrada ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_position_rejects_empty_title():
    out = await create_position.ainvoke({"tenant_id": VALID_TENANT, "title": "   "})
    assert out.startswith("Error")
    assert "título" in out.lower()


@pytest.mark.asyncio
async def test_create_position_rejects_bad_tenant_uuid():
    out = await create_position.ainvoke({"tenant_id": "no-es-uuid", "title": "Backend dev"})
    assert "no es un identificador válido" in out


@pytest.mark.asyncio
async def test_list_positions_rejects_bad_tenant_uuid():
    out = await list_positions.ainvoke({"tenant_id": "xxx"})
    assert "no es un identificador válido" in out


@pytest.mark.asyncio
async def test_list_candidates_rejects_bad_position_uuid():
    out = await list_candidates.ainvoke({"tenant_id": VALID_TENANT, "position_id": "bad"})
    assert "no es un identificador válido" in out


@pytest.mark.asyncio
async def test_update_candidate_status_rejects_invalid_status():
    out = await update_candidate_status.ainvoke(
        {"tenant_id": VALID_TENANT, "candidate_id": VALID_POS, "new_status": "promoted"}
    )
    assert "Estado inválido" in out


@pytest.mark.asyncio
async def test_create_candidate_rejects_empty_name():
    out = await create_candidate.ainvoke({"tenant_id": VALID_TENANT, "name": ""})
    assert out.startswith("Error")
    assert "nombre" in out.lower()


# ── Degradación con gracia en process_cv ──────────────────────────────────────

@pytest.mark.asyncio
async def test_process_cv_bad_uuid_returns_friendly_error():
    out = await process_cv.ainvoke(
        {"tenant_id": "nope", "position_id": VALID_POS, "cv_file_path": "/tmp/cv.pdf"}
    )
    assert "no es un identificador válido" in out


@pytest.mark.asyncio
async def test_process_cv_missing_file_degrades():
    async def _raise(_path):
        raise FileNotFoundError("no such file")

    with patch("app.services.ai.cv_parser.parse_cv_file", side_effect=_raise):
        out = await process_cv.ainvoke(
            {"tenant_id": VALID_TENANT, "position_id": VALID_POS, "cv_file_path": "/x.pdf"}
        )
    assert out.startswith("Error")
    assert "no se encontró" in out


@pytest.mark.asyncio
async def test_process_cv_empty_text_degrades():
    async def _empty(_path):
        return ""

    with patch("app.services.ai.cv_parser.parse_cv_file", side_effect=_empty):
        out = await process_cv.ainvoke(
            {"tenant_id": VALID_TENANT, "position_id": VALID_POS, "cv_file_path": "/x.pdf"}
        )
    assert "no se pudo extraer texto" in out


@pytest.mark.asyncio
async def test_process_cv_llm_failure_degrades():
    async def _text(_path):
        return "Juan Pérez, Python, 5 años"

    async def _llm_down(_text):
        raise RuntimeError("LLM timeout")

    with patch("app.services.ai.cv_parser.parse_cv_file", side_effect=_text), patch(
        "app.services.ai.cv_parser.extract_cv_data", side_effect=_llm_down
    ):
        out = await process_cv.ainvoke(
            {"tenant_id": VALID_TENANT, "position_id": VALID_POS, "cv_file_path": "/x.pdf"}
        )
    assert "no se pudieron estructurar" in out
