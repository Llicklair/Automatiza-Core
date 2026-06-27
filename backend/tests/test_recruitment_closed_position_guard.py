"""Tests for the closed-position guard in upload_cv (service path).

Verifies:
1. CLOSED position → ValueError("cerrado"), zero Candidate rows created.
2. OPEN position → NOT blocked, Candidate IS created with status "new".
3. PAUSED position → NOT blocked (guard is status=="closed" only).
"""
from __future__ import annotations

import io
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.hr import Candidate, RecruitmentPosition

# ── helpers ──────────────────────────────────────────────────────────────────

async def _make_position(db: AsyncSession, tenant_id, status: str) -> RecruitmentPosition:
    pos = RecruitmentPosition(
        id=uuid4(),
        tenant_id=tenant_id,
        title="Puesto Test",
        status=status,
    )
    db.add(pos)
    await db.flush()
    return pos


async def _candidate_count(db: AsyncSession, tenant_id, position_id) -> int:
    result = await db.execute(
        select(Candidate).where(
            Candidate.tenant_id == tenant_id,
            Candidate.position_id == position_id,
        )
    )
    return len(result.scalars().all())


# ── tests ─────────────────────────────────────────────────────────────────────

class TestUploadCvClosedPositionGuard:

    @pytest.mark.asyncio
    async def test_closed_position_raises_value_error(
        self, db: AsyncSession, seed_tenant_and_user
    ):
        """upload_cv on a CLOSED position must raise ValueError before any I/O."""
        tenant, _, _ = seed_tenant_and_user
        pos = await _make_position(db, tenant.id, "closed")

        from app.services.hr.commands import upload_cv

        dummy_file = io.BytesIO(b"%PDF-1.4 dummy")

        with pytest.raises(ValueError, match="cerrado"):
            await upload_cv(
                db=db,
                tenant_id=tenant.id,
                position_id=pos.id,
                file_name="cv.pdf",
                file_obj=dummy_file,
            )

        # Guard fires before commit → zero candidates must exist
        count = await _candidate_count(db, tenant.id, pos.id)
        assert count == 0, f"Expected 0 candidates after guard, got {count}"

    @pytest.mark.asyncio
    async def test_open_position_not_blocked(
        self, db: AsyncSession, seed_tenant_and_user, monkeypatch
    ):
        """upload_cv on an OPEN position must NOT be blocked; Candidate is created."""
        tenant, _, _ = seed_tenant_and_user
        pos = await _make_position(db, tenant.id, "open")

        # Patch at point-of-use inside commands.py to avoid real PDF parse + LLM
        async def _fake_parse(path):
            return "Texto del CV de prueba"

        async def _fake_extract(text):
            return {
                "name": "Candidato Test",
                "email": "cand@test.com",
                "phone": "600000001",
                "skills": ["Python"],
                "experience_years": 2,
                "languages": [],
                "education": "FP Superior",
                "summary": "Resumen prueba",
            }

        # The imports inside upload_cv are local ("from app.services.ai.cv_parser import …")
        # so we patch the names on the module after it has been imported once.
        import app.services.ai.cv_parser as cv_parser_module

        monkeypatch.setattr(cv_parser_module, "parse_cv_file", _fake_parse)
        monkeypatch.setattr(cv_parser_module, "extract_cv_data", _fake_extract)

        dummy_file = io.BytesIO(b"%PDF-1.4 dummy")

        from app.services.hr.commands import upload_cv

        candidate = await upload_cv(
            db=db,
            tenant_id=tenant.id,
            position_id=pos.id,
            file_name="cv.pdf",
            file_obj=dummy_file,
        )

        assert candidate is not None
        assert candidate.status == "new"
        assert candidate.position_id == pos.id

        count = await _candidate_count(db, tenant.id, pos.id)
        assert count == 1, f"Expected 1 candidate for open position, got {count}"

    @pytest.mark.asyncio
    async def test_paused_position_not_blocked(
        self, db: AsyncSession, seed_tenant_and_user, monkeypatch
    ):
        """upload_cv on a PAUSED position must NOT be blocked (guard is closed-only)."""
        tenant, _, _ = seed_tenant_and_user
        pos = await _make_position(db, tenant.id, "paused")

        import app.services.ai.cv_parser as cv_parser_module

        async def _fake_parse(path):
            return "Texto del CV pausado"

        async def _fake_extract(text):
            return {
                "name": "Candidato Pausado",
                "email": "paused@test.com",
                "phone": None,
                "skills": [],
                "experience_years": 0,
                "languages": [],
                "education": None,
                "summary": None,
            }

        monkeypatch.setattr(cv_parser_module, "parse_cv_file", _fake_parse)
        monkeypatch.setattr(cv_parser_module, "extract_cv_data", _fake_extract)

        dummy_file = io.BytesIO(b"%PDF-1.4 dummy")

        from app.services.hr.commands import upload_cv

        candidate = await upload_cv(
            db=db,
            tenant_id=tenant.id,
            position_id=pos.id,
            file_name="cv.pdf",
            file_obj=dummy_file,
        )

        assert candidate is not None
        assert candidate.status == "new"

        count = await _candidate_count(db, tenant.id, pos.id)
        assert count == 1, f"Expected 1 candidate for paused position, got {count}"
