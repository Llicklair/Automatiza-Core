"""Tests para el folio correlativo de documentos de gestoría (2.8)."""
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.db.models.hr_documents import HRDocument
from app.services.hr.commands import approve_document


def _doc(tenant_id, status="draft"):
    return HRDocument(
        id=uuid4(), tenant_id=tenant_id, doc_type="contract",
        title="Contrato", content_html="<p>x</p>", status=status,
    )


@pytest.mark.asyncio
class TestHRDocNumbering:
    async def test_approve_assigns_correlative_folio(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        d1, d2 = _doc(tenant.id), _doc(tenant.id)
        db.add_all([d1, d2])
        await db.commit()

        r1 = await approve_document(d1.id, tenant.id, db)
        r2 = await approve_document(d2.id, tenant.id, db)

        year = datetime.now(UTC).year
        assert r1["doc_number"] == f"DOC-{year}-0001"
        assert r2["doc_number"] == f"DOC-{year}-0002"

    async def test_reapprove_keeps_same_number(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        d = _doc(tenant.id)
        db.add(d)
        await db.commit()

        r1 = await approve_document(d.id, tenant.id, db)
        r2 = await approve_document(d.id, tenant.id, db)
        assert r1["doc_number"] == r2["doc_number"]

    async def test_numbering_is_per_tenant(
        self, db, seed_tenant_and_user, seed_second_tenant_and_user
    ):
        tenant_a, _ua, _ta = seed_tenant_and_user
        tenant_b, _ub, _tb = seed_second_tenant_and_user
        da, db_doc = _doc(tenant_a.id), _doc(tenant_b.id)
        db.add_all([da, db_doc])
        await db.commit()

        ra = await approve_document(da.id, tenant_a.id, db)
        rb = await approve_document(db_doc.id, tenant_b.id, db)
        year = datetime.now(UTC).year
        # Cada tenant arranca su propia serie en 0001.
        assert ra["doc_number"] == f"DOC-{year}-0001"
        assert rb["doc_number"] == f"DOC-{year}-0001"
