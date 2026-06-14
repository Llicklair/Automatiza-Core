"""Tests para la búsqueda semántica sin pgvector — cálculo coseno en Python
sobre embeddings almacenados como JSONB en document_embeddings.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from app.agents.agent_tools.semantic_search import (
    _cosine_distance,
    cosine_topk,
    is_missing_table_or_extension,
    similarity_from_distance,
)
from sqlalchemy.ext.asyncio import AsyncSession


class TestCosineDistance:
    def test_identical_vectors_distance_zero(self):
        a = [1.0, 0.0, 0.0]
        assert _cosine_distance(a, a) == pytest.approx(0.0, abs=1e-6)

    def test_orthogonal_vectors_distance_one(self):
        assert _cosine_distance([1.0, 0.0], [0.0, 1.0]) == pytest.approx(1.0, abs=1e-6)

    def test_opposite_vectors_distance_two(self):
        assert _cosine_distance([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(2.0, abs=1e-6)

    def test_zero_vector_returns_max_distance(self):
        assert _cosine_distance([0.0, 0.0], [1.0, 1.0]) == 2.0

    def test_length_mismatch_returns_max_distance(self):
        assert _cosine_distance([1.0], [1.0, 0.0]) == 2.0

    def test_similarity_clamped_to_zero(self):
        # distance > 1 (opuestos) → similarity 0, no negativo
        assert similarity_from_distance(2.0) == 0.0
        assert similarity_from_distance(1.5) == 0.0


class TestIsMissingTableOrExtension:
    def test_sqlstate_42P01_is_missing(self):
        class _E(Exception):
            sqlstate = "42P01"

        assert is_missing_table_or_extension(_E())

    def test_sqlstate_42704_is_missing(self):
        class _E(Exception):
            sqlstate = "42704"

        assert is_missing_table_or_extension(_E())

    def test_text_does_not_exist_is_missing(self):
        e = Exception('relation "document_embeddings" does not exist')
        assert is_missing_table_or_extension(e)

    def test_unrelated_error_is_not_missing(self):
        assert not is_missing_table_or_extension(ValueError("bad value"))


class TestCosineTopkAgainstDB:
    @pytest.mark.asyncio
    async def test_topk_returns_closest_first(
        self, db: AsyncSession, seed_tenant_and_user
    ):
        from app.db.models.embeddings import DocumentEmbedding

        tenant, _user, _token = seed_tenant_and_user

        # Tres embeddings sintéticos. Query = [1, 0, 0]:
        # - far → [-1, 0, 0]  distance ~= 2.0
        # - mid → [0, 1, 0]   distance ~= 1.0
        # - near → [0.9, 0.1, 0]  distance ~= 0.006
        rows = [
            DocumentEmbedding(
                id=uuid4(),
                document_id=uuid4(),
                tenant_id=tenant.id,
                chunk_index="0",
                text_content="far",
                embedding=[-1.0, 0.0, 0.0],
            ),
            DocumentEmbedding(
                id=uuid4(),
                document_id=uuid4(),
                tenant_id=tenant.id,
                chunk_index="0",
                text_content="mid",
                embedding=[0.0, 1.0, 0.0],
            ),
            DocumentEmbedding(
                id=uuid4(),
                document_id=uuid4(),
                tenant_id=tenant.id,
                chunk_index="0",
                text_content="near",
                embedding=[0.9, 0.1, 0.0],
            ),
        ]
        db.add_all(rows)
        await db.commit()

        scored = await cosine_topk(
            db,
            tenant_id=str(tenant.id),
            query_vector=[1.0, 0.0, 0.0],
            top_k=2,
        )
        assert len(scored) == 2
        assert scored[0][0].text_content == "near"
        assert scored[1][0].text_content == "mid"

    @pytest.mark.asyncio
    async def test_topk_filters_by_tenant(
        self, db: AsyncSession, seed_tenant_and_user, seed_second_tenant_and_user
    ):
        from app.db.models.embeddings import DocumentEmbedding

        tenant_a, _ua, _ta = seed_tenant_and_user
        tenant_b, _ub, _tb = seed_second_tenant_and_user

        db.add_all(
            [
                DocumentEmbedding(
                    id=uuid4(), document_id=uuid4(), tenant_id=tenant_a.id,
                    chunk_index="0", text_content="A doc",
                    embedding=[1.0, 0.0, 0.0],
                ),
                DocumentEmbedding(
                    id=uuid4(), document_id=uuid4(), tenant_id=tenant_b.id,
                    chunk_index="0", text_content="B doc",
                    embedding=[1.0, 0.0, 0.0],
                ),
            ]
        )
        await db.commit()

        scored = await cosine_topk(
            db,
            tenant_id=str(tenant_a.id),
            query_vector=[1.0, 0.0, 0.0],
            top_k=10,
        )
        assert len(scored) == 1
        assert scored[0][0].text_content == "A doc"
