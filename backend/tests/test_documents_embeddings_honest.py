"""_store_embeddings distingue 'sin proveedor' de 'falló' y no traga el error.

Antes: sin embedder o ante una excepción devolvía cadena vacía / un texto sin
log, y el documento se marcaba completado sin rastro del problema.
"""

import uuid
from unittest.mock import patch

import pytest

from app.agents.documents.tools import _store_embeddings

pytestmark = pytest.mark.asyncio


async def test_sin_proveedor_lo_indica_no_vacio():
    with patch("app.agents.documents.tools.get_embedder", return_value=None):
        res = await _store_embeddings("t", "d", "texto del documento", None)
    assert res.strip() != ""
    assert "texto" in res.lower()  # avisa que será buscable por texto


async def test_fallo_de_embeddings_no_se_traga():
    class _Boom:
        async def aembed_documents(self, _texts):
            raise RuntimeError("boom de embeddings")

    with patch("app.agents.documents.tools.get_embedder", return_value=_Boom()):
        res = await _store_embeddings("t", str(uuid.uuid4()), "texto largo del doc", None)

    assert "no generados" in res.lower()
    assert "boom de embeddings" in res
