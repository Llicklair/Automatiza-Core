"""
RAG agent — tools: búsqueda semántica y respuesta desde documentos.
"""

from __future__ import annotations

import logging
import uuid

import sqlalchemy as sa
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge
from app.agents.agent_tools.semantic_search import (
    cosine_topk,
    is_missing_table_or_extension as _is_missing_table_or_extension,
)
from app.core.llm_factory import get_embedder, get_llm
from app.db.base import AsyncSessionLocal

logger = logging.getLogger(__name__)


_SEMANTIC_DISABLED_NOTE = (
    "(búsqueda semántica no habilitada en este tenant — la tabla "
    "'document_embeddings' aún no está creada; se usaron solo "
    "coincidencias por nombre/categoría)"
)


def _get_llm():
    return get_llm(temperature=0)


@tool
async def search_documents(tenant_id: str, query: str, top_k: int = 5) -> str:
    """
    Busca fragmentos relevantes en los documentos del tenant usando búsqueda
    híbrida: nombre de archivo + búsqueda semántica con pgvector.

    Args:
        tenant_id: ID del tenant
        query: Texto de búsqueda en lenguaje natural
        top_k: Número máximo de fragmentos a devolver (por defecto 5)
    """
    from app.db.models.models import TenantDocument

    retrieved_chunks = []
    source_names = set()
    semantic_disabled = False

    try:
        async with AsyncSessionLocal() as db:
            stmt_files = (
                sa.select(TenantDocument)
                .where(
                    TenantDocument.tenant_id == uuid.UUID(tenant_id),
                    sa.or_(
                        TenantDocument.file_name.ilike(f"%{query}%"),
                        TenantDocument.category.ilike(f"%{query}%"),
                    ),
                )
                .limit(2)
            )
            res_files = await db.execute(stmt_files)
            for fd in res_files.scalars().all():
                source_names.add(fd.file_name)
                retrieved_chunks.append(
                    f"📄 {fd.file_name} [{fd.category}]: {fd.parsed_content[:500] if fd.parsed_content else 'Sin contenido extraído'}"
                )

            embedder = get_embedder()
            if embedder:
                from app.db.models.auth import Tenant

                j_res = await db.execute(
                    sa.select(Tenant.jurisdiction).where(Tenant.id == uuid.UUID(tenant_id))
                )
                jurisdiction = j_res.scalar() or "ES_TAX"

                query_vector = await embedder.aembed_query(query)
                # Coseno en Python (sin pgvector) — la app desktop no lo
                # incluye. Si la tabla aún no está creada, marcamos
                # disabled y conservamos los matches por filename.
                try:
                    scored = await cosine_topk(
                        db,
                        tenant_id=tenant_id,
                        query_vector=query_vector,
                        top_k=top_k,
                        jurisdiction=jurisdiction,
                    )
                    for match, _dist in scored:
                        doc_name_res = await db.execute(
                            sa.select(TenantDocument.file_name).where(
                                TenantDocument.id == match.document_id
                            )
                        )
                        doc_name = doc_name_res.scalar()
                        if doc_name:
                            source_names.add(doc_name)
                        page_info = f" [Pág. {match.page_number}]" if match.page_number else ""
                        type_info = f" ({match.element_type})" if match.element_type else ""
                        retrieved_chunks.append(
                            f"{match.text_content}{page_info}{type_info}"
                        )
                except Exception as ve:
                    if _is_missing_table_or_extension(ve):
                        semantic_disabled = True
                    else:
                        raise
    except Exception as e:
        if _is_missing_table_or_extension(e):
            semantic_disabled = True
        else:
            return f"Error en búsqueda: {e}"

    if not retrieved_chunks:
        if semantic_disabled:
            return (
                f"No se encontraron documentos por nombre/categoría para "
                f"'{query}'. {_SEMANTIC_DISABLED_NOTE}"
            )
        return f"No se encontraron documentos relevantes para: '{query}'"

    result = (
        f"Fragmentos encontrados ({len(retrieved_chunks)}) de {len(source_names)} documento(s):\n"
    )
    if semantic_disabled:
        result += f"{_SEMANTIC_DISABLED_NOTE}\n"
    result += f"Fuentes: {', '.join(source_names)}\n\n"
    for idx, chunk in enumerate(retrieved_chunks, 1):
        result += f"--- Fragmento {idx} ---\n{chunk[:500]}\n\n"
    return result


@tool
async def answer_from_documents(tenant_id: str, question: str, top_k: int = 5) -> str:
    """
    Responde una pregunta basándose ÚNICAMENTE en los documentos almacenados.

    Args:
        tenant_id: ID del tenant
        question: Pregunta del usuario en lenguaje natural
        top_k: Número de fragmentos de contexto a usar (por defecto 5)
    """
    from app.db.models.models import TenantDocument

    retrieved_chunks = []
    source_names = set()
    semantic_disabled = False

    try:
        async with AsyncSessionLocal() as db:
            stmt_files = (
                sa.select(TenantDocument)
                .where(
                    TenantDocument.tenant_id == uuid.UUID(tenant_id),
                    sa.or_(
                        TenantDocument.file_name.ilike(f"%{question}%"),
                        TenantDocument.category.ilike(f"%{question}%"),
                    ),
                )
                .limit(2)
            )
            res_files = await db.execute(stmt_files)
            for fd in res_files.scalars().all():
                source_names.add(fd.file_name)
                retrieved_chunks.append(
                    {
                        "doc_id": str(fd.id),
                        "text": f"Documento: {fd.file_name}. Categoría: {fd.category}. Contenido: {fd.parsed_content[:500] if fd.parsed_content else 'N/A'}",
                    }
                )

            embedder = get_embedder()
            if embedder:
                from app.db.models.auth import Tenant

                j_res = await db.execute(
                    sa.select(Tenant.jurisdiction).where(Tenant.id == uuid.UUID(tenant_id))
                )
                jurisdiction = j_res.scalar() or "ES_TAX"

                query_vector = await embedder.aembed_query(question)
                try:
                    scored = await cosine_topk(
                        db,
                        tenant_id=tenant_id,
                        query_vector=query_vector,
                        top_k=top_k,
                        jurisdiction=jurisdiction,
                    )
                    for match, _dist in scored:
                        doc_name_res = await db.execute(
                            sa.select(TenantDocument.file_name).where(
                                TenantDocument.id == match.document_id
                            )
                        )
                        doc_name = doc_name_res.scalar()
                        if doc_name:
                            source_names.add(doc_name)
                        page_ref = (
                            f" [Página {match.page_number}]" if match.page_number else ""
                        )
                        retrieved_chunks.append(
                            {
                                "doc_id": str(match.document_id),
                                "text": f"{match.text_content}{page_ref}",
                            }
                        )
                except Exception as ve:
                    if _is_missing_table_or_extension(ve):
                        semantic_disabled = True
                    else:
                        raise
    except Exception as e:
        if _is_missing_table_or_extension(e):
            semantic_disabled = True
        else:
            return f"Error buscando documentos: {e}"

    if not retrieved_chunks:
        return "No he encontrado documentos en tu base de datos que contengan información relevante para responder esta pregunta."

    contexto = ""
    for idx, c in enumerate(retrieved_chunks, 1):
        contexto += f"\n--- Fragmento {idx} ---\n{c['text']}\n"

    llm = _get_llm()
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content="Eres un asistente empresarial experto. Responde ÚNICAMENTE basándote en los fragmentos proporcionados. Si no puedes responder, dilo claramente. Nunca inventes datos."
                ),
                HumanMessage(content=f"DOCUMENTOS:\n{contexto}\n\nPREGUNTA: {question}"),
            ]
        )
        answer = response.content
    except Exception as e:
        return f"Error generando respuesta: {e}"

    sources_str = ", ".join(source_names) if source_names else "documentos del sistema"
    return f"{answer}\n\n📎 Fuentes: {sources_str} ({len(retrieved_chunks)} fragmentos consultados)"


tools = [
    search_documents,
    answer_from_documents,
    create_document,
    list_tenant_documents,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
]
