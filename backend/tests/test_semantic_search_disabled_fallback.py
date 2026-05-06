"""Cuando la tabla document_embeddings o la extensión pgvector no están
instaladas (caso del Postgres portable que distribuye la app), las
tools de búsqueda semántica deben devolver un mensaje útil al LLM
en vez de propagar 'Error en búsqueda semántica: relation
"document_embeddings" does not exist'.
"""
from __future__ import annotations

import pytest


class _FakeUndefinedTable(Exception):
    sqlstate = "42P01"

    def __str__(self):
        return 'relation "document_embeddings" does not exist'


class TestSemanticSearchGracefulDisabled:
    def test_disabled_message_mentions_alternative_tool(self):
        from importlib import import_module

        mod = import_module("app.agents.documents.tools")
        assert "list_tenant_documents" in mod._SEMANTIC_DISABLED_MSG
        assert "document_embeddings" in mod._SEMANTIC_DISABLED_MSG

    def test_helper_detects_sqlstate_42P01(self):
        from app.agents.documents.tools import _is_missing_table_or_extension

        assert _is_missing_table_or_extension(_FakeUndefinedTable())

    def test_helper_detects_message_text(self):
        from app.agents.documents.tools import _is_missing_table_or_extension

        e = Exception('relation "document_embeddings" does not exist')
        assert _is_missing_table_or_extension(e)

    def test_helper_detects_pgvector_missing(self):
        from app.agents.documents.tools import _is_missing_table_or_extension

        e = Exception('type "vector" does not exist')
        assert _is_missing_table_or_extension(e)

    def test_helper_passes_unrelated_errors(self):
        from app.agents.documents.tools import _is_missing_table_or_extension

        assert not _is_missing_table_or_extension(Exception("some other error"))
        assert not _is_missing_table_or_extension(ValueError("bad input"))
