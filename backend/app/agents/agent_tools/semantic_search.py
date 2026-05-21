"""Búsqueda semántica sin pgvector: cálculo coseno en Python.

La app desktop distribuye un Postgres portable sin la extensión pgvector,
por lo que las consultas con `<=>` o `cosine_distance(...)` no son
viables. Almacenamos los embeddings como JSONB (lista de floats) y
calculamos similitud coseno en Python con NumPy.

Apropiado para PYMEs con hasta ~5.000 chunks por tenant: la consulta
trae todos los embeddings filtrados por tenant_id (y opcionalmente
jurisdiction) y rankea en memoria. Para volúmenes mayores, migrar a
pgvector y/o limitar por categoría/fecha antes del ranking.
"""
from __future__ import annotations

import logging
import math
import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from app.db.models.embeddings import DocumentEmbedding

_logger = logging.getLogger(__name__)


def _cosine_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """Distancia coseno entre dos vectores (1 - similaridad). Devuelve
    2.0 si alguno tiene norma 0 o longitudes incompatibles — peor caso,
    nunca aparecerá en top_k."""
    if not a or not b or len(a) != len(b):
        return 2.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 2.0
    return 1.0 - dot / (math.sqrt(na) * math.sqrt(nb))


async def cosine_topk(
    db,
    *,
    tenant_id: str,
    query_vector: Sequence[float],
    top_k: int = 5,
    jurisdiction: str | None = None,
    include_no_jurisdiction: bool = True,
    employee_id: str | None = None,
) -> list[tuple[DocumentEmbedding, float]]:
    """Devuelve los top_k DocumentEmbedding del tenant ordenados por
    proximidad coseno al query_vector.

    Args:
        db: AsyncSession activa.
        tenant_id: UUID en string.
        query_vector: lista de floats del embedding de la consulta.
        top_k: número de resultados a devolver.
        jurisdiction: si se especifica, filtra por jurisdicción.
        include_no_jurisdiction: si True y se filtra jurisdiction, también
            incluye filas con jurisdiction=NULL (datos legacy).
        employee_id: si se pasa, el resultado incluye embeddings públicos
            del tenant (employee_id IS NULL) **y** los privados de ese
            empleado. Si es None, sólo se devuelven los públicos. Sólo
            tiene efecto si el empleado tiene `knowledge_enabled=True`
            (la decisión la toma la capa que invoca esta función).

    Returns:
        Lista de (DocumentEmbedding, distance) en orden ascendente de
        distance (más cercano primero). Distance ∈ [0, 2].
    """
    stmt = sa.select(DocumentEmbedding).where(
        DocumentEmbedding.tenant_id == uuid.UUID(tenant_id),
    )
    if jurisdiction is not None:
        if include_no_jurisdiction:
            stmt = stmt.where(
                sa.or_(
                    DocumentEmbedding.jurisdiction == jurisdiction,
                    DocumentEmbedding.jurisdiction.is_(None),
                )
            )
        else:
            stmt = stmt.where(DocumentEmbedding.jurisdiction == jurisdiction)

    if employee_id is None:
        stmt = stmt.where(DocumentEmbedding.employee_id.is_(None))
    else:
        stmt = stmt.where(
            sa.or_(
                DocumentEmbedding.employee_id.is_(None),
                DocumentEmbedding.employee_id == uuid.UUID(employee_id),
            )
        )

    result = await db.execute(stmt)
    rows: list[DocumentEmbedding] = list(result.scalars().all())

    scored: list[tuple[DocumentEmbedding, float]] = []
    for row in rows:
        emb = row.embedding
        # JSONB carga como lista directamente. Si llegase un string
        # (compatibilidad con datos antiguos serializados), parsearlo.
        if isinstance(emb, str):
            try:
                import json as _json

                emb = _json.loads(emb)
            except (ValueError, TypeError) as parse_err:
                _logger.warning(
                    "[semantic_search] embedding corrupto en row id=%s doc_id=%s tenant=%s: %s",
                    getattr(row, "id", "?"),
                    getattr(row, "document_id", "?"),
                    getattr(row, "tenant_id", "?"),
                    parse_err,
                )
                continue
        if not isinstance(emb, list):
            _logger.warning(
                "[semantic_search] embedding type inesperado %s en row id=%s doc_id=%s",
                type(emb).__name__,
                getattr(row, "id", "?"),
                getattr(row, "document_id", "?"),
            )
            continue
        scored.append((row, _cosine_distance(query_vector, emb)))

    scored.sort(key=lambda x: x[1])
    return scored[:top_k]


def similarity_from_distance(distance: float) -> float:
    """Convierte distancia coseno [0, 2] a similaridad [0, 1] truncada."""
    return max(0.0, 1.0 - distance)


def is_missing_table_or_extension(exc: Exception) -> bool:
    """Detecta el error pgsql cuando la infraestructura de búsqueda
    semántica (tabla document_embeddings o extensión vector) no está
    instalada — código sqlstate 42P01 (UndefinedTable) o 42704
    (UndefinedObject)."""
    sqlstate = getattr(exc, "sqlstate", None) or getattr(
        getattr(exc, "orig", None), "sqlstate", None
    )
    if sqlstate in ("42P01", "42704"):
        return True
    err = str(exc).lower()
    return (
        "document_embeddings" in err
        and ("does not exist" in err or "no existe la relaci" in err)
    ) or ('type "vector"' in err and "does not exist" in err)
