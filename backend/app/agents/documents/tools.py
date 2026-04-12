"""
Herramientas del agente de documentos.
"""

import json
import logging
import os
import re
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
    update_existing_document,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge
from app.core.llm_factory import get_embedder, get_llm
from app.core.prompt_sanitizer import sanitize_user_input
from app.prompts import load_prompt
from app.services.document_classifier import classify_by_rules
from app.services.pdf.parser import parse_pdf
from app.services.smart_chunker import smart_chunk

logger = logging.getLogger(__name__)


def _get_llm():
    return get_llm(temperature=0)


def _get_llm_json():
    return get_llm(temperature=0, format_output="json")


# ─── Modelos ──────────────────────────────────────────────────────────────────


class ClassifiedDocument(BaseModel):
    document_type: str
    confidence: float | None = 0.9
    language: str = "es"
    requires_action: bool = False
    suggested_action: str | None = None
    key_entities: dict = Field(default_factory=dict)
    summary: str = ""


CLASSIFICATION_PROMPT = load_prompt("documents_classification")


# ─── Herramientas del agente ──────────────────────────────────────────────────


@tool
async def classify_document(tenant_id: str, document_id: str) -> str:
    """
    Clasifica un documento subido: detecta tipo (factura, contrato, extracto, nómina),
    extrae entidades clave (emisor, receptor, importe, fecha), genera resumen,
    y crea embeddings para búsqueda semántica RAG.

    Args:
        tenant_id: ID del tenant
        document_id: ID del documento en TenantDocument (ya subido al sistema)
    """
    return await _classify_document_async(tenant_id, document_id)


async def _classify_document_async(tenant_id: str, document_id: str) -> str:
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Client, TenantDocument

    # ── Leer documento de BD y disco ──
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TenantDocument).where(
                    TenantDocument.tenant_id == UUID(tenant_id),
                    TenantDocument.id == UUID(document_id),
                )
            )
            doc = result.scalar_one_or_none()

            if not doc:
                return f"Error: Documento {document_id} no encontrado."

            file_bytes = None
            raw_text = ""

            if doc.file_path and os.path.exists(doc.file_path):
                with open(doc.file_path, "rb") as f:
                    file_bytes = f.read()

            # Extraer texto con OpenDataLoader (fallback a pypdf)
            parsed_doc = None
            if file_bytes and doc.file_type and "pdf" in doc.file_type.lower():
                try:
                    parsed_doc = parse_pdf(
                        file_path=doc.file_path
                        if doc.file_path and os.path.exists(doc.file_path)
                        else None,
                        file_bytes=file_bytes,
                    )
                    raw_text = parsed_doc.markdown
                    logger.info(
                        "PDF parseado con %s: %d páginas, %d elementos",
                        parsed_doc.parser_used,
                        parsed_doc.total_pages,
                        len(parsed_doc.elements),
                    )
                except Exception as e:
                    logger.warning("Error parsing PDF: %s", e)
            elif file_bytes:
                try:
                    raw_text = file_bytes.decode("utf-8", errors="ignore")[:5000]
                except Exception as _e:
                    logger.warning("Error decodificando bytes de documento: %s", _e)

            if doc.parsed_content and not raw_text:
                raw_text = doc.parsed_content[:5000]

            if not raw_text:
                return f"Error: No se pudo extraer texto del documento '{doc.file_name}'."

    except Exception as e:
        return f"Error leyendo documento: {e}"

    # ── Clasificar: primero reglas (0 tokens), luego LLM si ambiguo ──
    rule_result = classify_by_rules(raw_text)
    logger.info(
        "Clasificación por reglas: %s (confianza=%.0f%%, needs_llm=%s)",
        rule_result.document_type,
        rule_result.confidence * 100,
        rule_result.needs_llm,
    )

    if not rule_result.needs_llm:
        # Clasificación mecánica — 0 tokens LLM
        classified = ClassifiedDocument(
            document_type=rule_result.document_type,
            confidence=rule_result.confidence,
            key_entities=rule_result.key_entities,
            summary=f"Documento clasificado por reglas como {rule_result.document_type}",
        )
    else:
        # Fallback a LLM para documentos ambiguos
        llm = _get_llm_json()
        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(content=CLASSIFICATION_PROMPT),
                    HumanMessage(
                        content=f"Clasifica este documento:\n\n{sanitize_user_input(raw_text[:4500])}"
                    ),
                ]
            )
            raw_content = (response.content or "").strip()
            # Strip markdown code fences if present
            if raw_content.startswith("```"):
                raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content)
                raw_content = re.sub(r"\s*```$", "", raw_content)
            if not raw_content:
                logger.warning(
                    "LLM returned empty response for document classification, using rule fallback"
                )
                classified = ClassifiedDocument(
                    document_type=rule_result.document_type,
                    confidence=rule_result.confidence,
                    key_entities=rule_result.key_entities,
                    summary=f"Clasificado por reglas (LLM sin respuesta): {rule_result.document_type}",
                )
            else:
                data_dict = json.loads(raw_content)
                classified = ClassifiedDocument(**data_dict)
        except Exception as e:
            logger.warning("LLM classification failed (%s), falling back to rules", e)
            classified = ClassifiedDocument(
                document_type=rule_result.document_type,
                confidence=max(rule_result.confidence, 0.5),
                key_entities=rule_result.key_entities,
                summary=f"Clasificado por reglas (LLM falló): {rule_result.document_type}",
            )

    # ── Extraer NIFs y crear/vincular cliente ──
    nif_pattern = re.compile(
        r"\b([A-Z][- ]?\d{7}[- ]?[A-Z0-9]|\d{8}[- ]?[A-Z]|[XYZ][- ]?\d{7}[- ]?[A-Z])\b"
    )
    raw_nifs = nif_pattern.findall(raw_text.upper())
    nifs_found = list(dict.fromkeys([n.replace("-", "").replace(" ", "") for n in raw_nifs]))

    client_info = ""
    if nifs_found:
        primary_nif = nifs_found[0]
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import select as sel

                res = await db.execute(
                    sel(Client).where(
                        Client.tenant_id == UUID(tenant_id),
                        Client.nif == primary_nif,
                    )
                )
                existing = res.scalar_one_or_none()
                if existing:
                    client_info = f"\nCliente vinculado: {existing.name} (NIF: {primary_nif})"
                else:
                    # Crear cliente desde datos del documento
                    new_client = Client(
                        tenant_id=UUID(tenant_id),
                        nif=primary_nif,
                        name=classified.key_entities.get("emisor") or f"Contacto {primary_nif}",
                        client_type="supplier",
                    )
                    db.add(new_client)
                    await db.commit()
                    client_info = f"\nNuevo cliente creado: {new_client.name} (NIF: {primary_nif})"
        except Exception as e:
            client_info = f"\nError vinculando cliente: {e}"

    # ── Generar embeddings para RAG (chunking inteligente) ──
    embeddings_info = ""
    try:
        embedder = get_embedder()
        if embedder and raw_text.strip():
            from app.db.models.embeddings import DocumentEmbedding

            # Chunking inteligente si tenemos elementos estructurados
            if parsed_doc and parsed_doc.elements:
                doc_chunks = smart_chunk(parsed_doc.elements)
            else:
                # Fallback: chunking mecánico para archivos no-PDF
                chunk_size = 1500
                doc_chunks = []
                from app.services.smart_chunker import Chunk

                for i in range(0, len(raw_text), chunk_size):
                    doc_chunks.append(Chunk(text=raw_text[i : i + chunk_size]))

            chunk_texts = [c.text for c in doc_chunks]
            vectors = await embedder.aembed_documents(chunk_texts)

            async with AsyncSessionLocal() as db:
                # Obtener jurisdicción del tenant para stamping
                import sqlalchemy as _sa

                from app.db.models.auth import Tenant

                _j_res = await db.execute(
                    _sa.select(Tenant.jurisdiction).where(Tenant.id == UUID(tenant_id))
                )
                _jurisdiction = _j_res.scalar() or "ES_TAX"

                for i, (chunk, vector) in enumerate(zip(doc_chunks, vectors)):
                    emb = DocumentEmbedding(
                        document_id=document_id,
                        tenant_id=UUID(tenant_id),
                        chunk_index=str(i),
                        text_content=chunk.text,
                        page_number=chunk.page_number or None,
                        element_type=chunk.element_type or None,
                        bounding_box=chunk.bounding_box or None,
                        jurisdiction=_jurisdiction,
                        embedding=vector,
                    )
                    db.add(emb)
                await db.commit()
            parser_label = f" ({parsed_doc.parser_used})" if parsed_doc else ""
            embeddings_info = f"\nEmbeddings RAG{parser_label}: {len(doc_chunks)} chunks indexados para búsqueda semántica."
    except Exception as e:
        embeddings_info = f"\nEmbeddings no generados: {e}"

    # ── Actualizar documento en BD con clasificación ──
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select as sel2

            result = await db.execute(
                sel2(TenantDocument).where(TenantDocument.id == UUID(document_id))
            )
            doc = result.scalar_one_or_none()
            if doc:
                doc.parsed_content = raw_text[:3000]
                doc.status = "completed"
                await db.commit()
    except Exception:
        logger.warning(
            "Failed to update parsed_content for document %s", document_id, exc_info=True
        )

    # ── Emitir evento ──
    try:
        from app.db.base import AsyncSessionLocal as ASL
        from app.services.event_bus import emit_event

        async with ASL() as db_ev:
            await emit_event(
                db=db_ev,
                tenant_id=UUID(tenant_id),
                user_id=None,
                event_name="document_processed",
                context={
                    "document_id": document_id,
                    "document_type": classified.document_type,
                    "key_entities": classified.key_entities,
                },
            )
    except Exception as e:
        logger.warning("Error emitiendo evento document_processed: %s", e)

    conf = classified.confidence if classified.confidence is not None else 0.9
    review_note = " ⚠️ Confianza baja, requiere revisión manual." if conf < 0.7 else ""

    return (
        f"Documento clasificado correctamente.\n"
        f"Tipo: {classified.document_type}\n"
        f"Confianza: {conf:.0%}\n"
        f"Resumen: {classified.summary}\n"
        f"Entidades: {json.dumps(classified.key_entities, ensure_ascii=False)}\n"
        f"Acción sugerida: {classified.suggested_action or 'Ninguna'}"
        f"{client_info}"
        f"{embeddings_info}"
        f"{review_note}"
    )


@tool
async def search_documents_semantic(tenant_id: str, query: str, limit: int = 5) -> str:
    """
    Busca documentos del tenant usando búsqueda semántica (RAG con pgvector).
    Útil para preguntas como "busca contratos de 2024" o "facturas de Acme".

    Args:
        tenant_id: ID del tenant
        query: Texto de búsqueda en lenguaje natural
        limit: Máximo de resultados (por defecto 5)
    """
    return await _search_documents_semantic_async(tenant_id, query, limit)


async def _search_documents_semantic_async(tenant_id: str, query: str, limit: int) -> str:
    from sqlalchemy import text

    from app.db.base import AsyncSessionLocal

    try:
        embedder = get_embedder()
        if not embedder:
            return "Error: No hay proveedor de embeddings configurado."

        query_vector = await embedder.aembed_query(query)

        async with AsyncSessionLocal() as db:
            # Búsqueda por coseno en pgvector
            stmt = text("""
                SELECT de.document_id, de.text_content,
                       de.embedding <=> :query_vec::vector AS distance
                FROM document_embeddings de
                WHERE de.tenant_id = :tid
                ORDER BY distance ASC
                LIMIT :lim
            """)
            result = await db.execute(
                stmt,
                {
                    "query_vec": str(query_vector),
                    "tid": tenant_id,
                    "lim": limit,
                },
            )
            rows = result.fetchall()

            if not rows:
                return f"No se encontraron documentos relevantes para: '{query}'"

            lines = []
            for doc_id, text_content, distance in rows:
                similarity = max(0, 1 - distance)
                snippet = text_content[:200].replace("\n", " ")
                lines.append(f"- Doc ID: {doc_id} | Relevancia: {similarity:.0%} | {snippet}...")

            return f"Resultados de búsqueda semántica ({len(rows)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error en búsqueda semántica: {e}"


# ─── Lista de herramientas ────────────────────────────────────────────────────

tools = [
    classify_document,
    search_documents_semantic,
    create_document,
    list_tenant_documents,
    update_existing_document,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
]
