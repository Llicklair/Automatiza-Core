"""
Tests for approve_document idempotency guard (services/hr/commands.py).

Covers:
1. Happy path: approving a PENDING doc assigns status, approved_at, and a valid doc_number.
2. Idempotency fix: a second approval must NOT overwrite approved_at or doc_number.
"""

import re
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.db.models.hr_documents import HRDocument
from app.services.hr.commands import approve_document


def _pending_doc(tenant_id):
    return HRDocument(
        id=uuid4(),
        tenant_id=tenant_id,
        doc_type="contract",
        title="Test Contract",
        content_html="<p>test</p>",
        status="draft",
    )


@pytest.mark.asyncio
class TestApproveDocumentIdempotency:
    async def test_happy_path_approve_pending(self, db, seed_tenant_and_user):
        """Approving a draft doc returns approved status, a timestamp, and a folio."""
        tenant, _u, _t = seed_tenant_and_user
        doc = _pending_doc(tenant.id)
        db.add(doc)
        await db.commit()

        result = await approve_document(doc.id, tenant.id, db)

        year = datetime.now(UTC).year
        assert result["status"] == "approved"
        assert result["approved_at"] is not None, "approved_at must be set on first approval"
        assert re.fullmatch(
            rf"DOC-{year}-\d{{4}}", result["doc_number"]
        ), f"doc_number format invalid: {result['doc_number']!r}"

    async def test_idempotency_approved_at_not_overwritten(self, db, seed_tenant_and_user):
        """
        Core fix: a second call to approve_document on an already-approved doc
        must return the SAME approved_at and doc_number — not overwrite them.
        """
        tenant, _u, _t = seed_tenant_and_user
        doc = _pending_doc(tenant.id)
        db.add(doc)
        await db.commit()

        # First approval — capture the legal timestamp and folio.
        r1 = await approve_document(doc.id, tenant.id, db)
        approved_at_1st = r1["approved_at"]
        doc_number_1st = r1["doc_number"]

        assert approved_at_1st is not None
        assert doc_number_1st is not None

        # Second approval — must be a no-op.
        r2 = await approve_document(doc.id, tenant.id, db)

        assert r2["status"] == "approved"
        assert r2["approved_at"] == approved_at_1st, (
            f"approved_at was overwritten: {approved_at_1st!r} -> {r2['approved_at']!r}"
        )
        assert r2["doc_number"] == doc_number_1st, (
            f"doc_number was overwritten: {doc_number_1st!r} -> {r2['doc_number']!r}"
        )

    async def test_idempotency_db_row_unchanged(self, db, seed_tenant_and_user):
        """
        After a second approval the DB row itself must reflect the original values
        — not the values from a hypothetical second write.
        """
        tenant, _u, _t = seed_tenant_and_user
        doc = _pending_doc(tenant.id)
        db.add(doc)
        await db.commit()

        r1 = await approve_document(doc.id, tenant.id, db)
        approved_at_1st = r1["approved_at"]
        doc_number_1st = r1["doc_number"]

        # Perform second approval, then refresh the ORM object from DB.
        await approve_document(doc.id, tenant.id, db)
        await db.refresh(doc)

        # The service returns tz-aware isoformat (+00:00) but SQLite stores naive
        # datetimes; strip the UTC suffix for comparison so we compare the same
        # wall-clock value regardless of tzinfo representation.
        db_approved_at = (
            doc.approved_at.isoformat().replace("+00:00", "") if doc.approved_at else None
        )
        approved_at_1st_naive = approved_at_1st.replace("+00:00", "") if approved_at_1st else None
        assert db_approved_at == approved_at_1st_naive, (
            "DB approved_at was mutated by the second approval"
        )
        assert doc.doc_number == doc_number_1st, (
            "DB doc_number was mutated by the second approval"
        )
        assert doc.status == "approved"
