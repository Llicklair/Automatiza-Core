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
from sqlalchemy import select

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
    update_existing_document,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge

# Documents agent NO genera informes PDF — esa responsabilidad recae en
# los agentes de dominio (billing, hr, crm, compliance...). Cuando el
# orchestrator decompone "Genera informe PDF" en sub-tareas y pasa por
# documents, sin esta restricción ambos sub-agents llamaban a la tool y
# se duplicaba el PDF resultante.
from app.core.llm_factory import get_embedder, get_llm
from app.core.prompt_sanitizer import sanitize_user_input
from app.db.base import AsyncSessionLocal
from app.db.models.auth import Tenant
from app.db.models.embeddings import DocumentEmbedding
from app.db.models.models import Client, TenantDocument
from app.prompts import load_prompt
from app.services.documents.classifier import classify_by_rules
from app.services.documents.smart_chunker import Chunk, smart_chunk
from app.services.pdf.parser import parse_pdf

logger = logging.getLogger(__name__)


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
async def import_invoice_document(
    tenant_id: str,
    document_id: str,
    confirm: bool = False,
    apply_stock: bool = False,
) -> str:
    """Asimila al ERP un documento de factura (escaneado o subido) como factura
    de COMPRA (recibida): hace OCR e importa de forma IDEMPOTENTE.

    FLUJO OBLIGATORIO: llama primero con confirm=False para mostrar los datos
    extraídos por OCR al usuario. Solo con confirm=True se persiste en el ERP.

    Úsalo cuando se quiera "registrar/importar al ERP" una factura que está en
    Documentos. Es SEGURO de reejecutar (apto para automatizaciones por evento):
      - Salta los documentos que el propio ERP genera (source="generated").
      - Salta los ya asimilados (documento ya enlazado a una factura).
      - Dedup por (proveedor + número): no crea duplicados.

    Args:
        tenant_id: ID del tenant
        document_id: ID del documento en TenantDocument
        confirm: False = previsualizar OCR sin importar (por defecto). True = importar.
        apply_stock: Solo cuando confirm=True. True = actualizar stock con las líneas
            de la factura. False = registrar solo la factura (sin tocar stock).

    Devuelve un resumen legible del resultado.
    """
    from app.services.billing.invoice_import import import_received_invoices
    from app.services.ocr import extract_invoice_data

    try:
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(TenantDocument).where(
                    TenantDocument.tenant_id == UUID(tenant_id),
                    TenantDocument.id == UUID(document_id),
                )
            )
            doc = res.scalar_one_or_none()
            if doc is None:
                return f"Error: documento {document_id} no encontrado."

            # Guarda anti-reflejo / anti-duplicado.
            if (doc.source or "uploaded") == "generated":
                return (
                    f"Omitido: '{doc.file_name}' es un documento generado por el "
                    "propio ERP (no una factura externa). No se importa."
                )
            if doc.entity_id is not None:
                return (
                    f"Omitido: '{doc.file_name}' ya estaba asimilado al ERP "
                    f"(factura {doc.entity_id}). No se reimporta."
                )
            if not doc.file_path or not os.path.exists(doc.file_path):
                return f"Error: no se encuentra el fichero de '{doc.file_name}'."

            with open(doc.file_path, "rb") as f:
                content = f.read()
            mime = doc.file_type or "application/pdf"
            uploaded_by = doc.uploaded_by
            tid = doc.tenant_id

            data = await extract_invoice_data(content, mime, tenant_id=tid, db=db)
            d = data.to_dict()

            if not confirm:
                # El preview leía claves inexistentes (supplier_name/base_amount/
                # total_amount) → siempre salía en blanco y marcaba "campos no
                # detectados". Las claves reales de extract_invoice_data().to_dict()
                # son emisor.{name,nif}, amount_base, amount_total (B21).
                emisor = d.get("emisor") or {}
                lines_count = len(d.get("lines") or [])
                missing = [
                    f
                    for f, v in [
                        ("proveedor", emisor.get("name")),
                        ("nº factura", d.get("invoice_number")),
                        ("total", d.get("amount_total")),
                    ]
                    if not v
                ]
                conf_note = (
                    f"\n⚠️ Campos no detectados: {', '.join(missing)} — revisa antes de confirmar."
                    if missing
                    else ""
                )
                return (
                    f"Datos extraídos de '{doc.file_name}':\n"
                    f"  Proveedor: {emisor.get('name') or '—'}\n"
                    f"  NIF proveedor: {emisor.get('nif') or '—'}\n"
                    f"  Nº factura: {d.get('invoice_number') or '—'}\n"
                    f"  Fecha: {d.get('issue_date') or '—'}\n"
                    f"  Base imponible: {d.get('amount_base') or '—'}€\n"
                    f"  IVA: {d.get('tax_amount') or '—'}€\n"
                    f"  Total: {d.get('amount_total') or '—'}€\n"
                    f"  Líneas detectadas: {lines_count}"
                    f"{conf_note}\n\n"
                    "¿Qué quieres hacer?\n"
                    "  (a) Solo registrar la factura de compra → responde 'registra' (apply_stock=False)\n"
                    "  (b) Registrar la factura Y actualizar el stock → responde 'registra con stock' (apply_stock=True)\n"
                    "  (c) Cancelar → no hagas nada"
                )

            # confirm=True: persistir en el ERP.
            d["source_document_id"] = str(doc.id)
            d["apply_stock"] = apply_stock
            results = await import_received_invoices(db, tid, [d], uploaded_by)

        r = results[0] if results else {}
        if not r.get("ok"):
            return f"No se pudo importar '{doc.file_name}': {r.get('error', 'error desconocido')}"
        if r.get("duplicate"):
            return (
                f"'{doc.file_name}' ya estaba en el ERP (factura {r.get('invoice_number')}). "
                "No se ha duplicado."
            )
        stock_note = " Stock actualizado con las líneas de la factura." if apply_stock else ""
        return (
            f"Factura importada al ERP desde '{doc.file_name}': "
            f"nº {r.get('invoice_number')} (id {r.get('invoice_id')}).{stock_note}"
        )
    except Exception as e:
        logger.exception("[IMPORT-DOC] fallo importando documento %s", document_id)
        return f"Error importando el documento: {e}"


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


async def _load_doc_and_extract_text(
    tenant_id: str, document_id: str
) -> "tuple[TenantDocument, str, object] | str":
    """Carga el documento de BD, lee bytes del disco y extrae texto. Devuelve (doc, raw_text, parsed_doc) o error."""
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
        if doc.file_path and os.path.exists(doc.file_path):
            with open(doc.file_path, "rb") as f:
                file_bytes = f.read()

        parsed_doc = None
        raw_text = ""
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
            except Exception as e:
                logger.warning("Error decodificando bytes de documento: %s", e)

        if doc.parsed_content and not raw_text:
            raw_text = doc.parsed_content[:5000]
        if not raw_text:
            return f"Error: No se pudo extraer texto del documento '{doc.file_name}'."
        return doc, raw_text, parsed_doc
    except Exception as e:
        return f"Error leyendo documento: {e}"


async def _link_client_from_nif(tenant_id: str, primary_nif: str, key_entities: dict) -> str:
    """Busca o crea un cliente a partir de un NIF extraído del documento. Devuelve client_info string."""
    try:
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(Client).where(Client.tenant_id == UUID(tenant_id), Client.nif == primary_nif)
            )
            existing = res.scalar_one_or_none()
            if existing:
                return f"\nCliente vinculado: {existing.name} (NIF: {primary_nif})"
            new_client = Client(
                tenant_id=UUID(tenant_id),
                nif=primary_nif,
                name=key_entities.get("emisor") or f"Contacto {primary_nif}",
                client_type="supplier",
            )
            db.add(new_client)
            await db.commit()
            return f"\nNuevo cliente creado: {new_client.name} (NIF: {primary_nif})"
    except Exception as e:
        return f"\nError vinculando cliente: {e}"


async def _store_embeddings(tenant_id: str, document_id: str, raw_text: str, parsed_doc) -> str:
    """Genera embeddings y los almacena en BD. Devuelve embeddings_info string."""
    try:
        embedder = get_embedder()
        if not embedder or not raw_text.strip():
            return ""

        if parsed_doc and parsed_doc.elements:
            doc_chunks = smart_chunk(parsed_doc.elements)
        else:
            chunk_size = 1500
            doc_chunks = [
                Chunk(text=raw_text[i : i + chunk_size])
                for i in range(0, len(raw_text), chunk_size)
            ]

        vectors = await embedder.aembed_documents([c.text for c in doc_chunks])

        async with AsyncSessionLocal() as db:
            j_res = await db.execute(
                select(Tenant.jurisdiction).where(Tenant.id == UUID(tenant_id))
            )
            jurisdiction = j_res.scalar() or "ES_TAX"
            for i, (chunk, vector) in enumerate(zip(doc_chunks, vectors)):
                db.add(
                    DocumentEmbedding(
                        document_id=UUID(str(document_id)),
                        tenant_id=UUID(tenant_id),
                        chunk_index=str(i),
                        text_content=chunk.text,
                        page_number=chunk.page_number or None,
                        element_type=chunk.element_type or None,
                        bounding_box=chunk.bounding_box or None,
                        jurisdiction=jurisdiction,
                        embedding=vector,
                    )
                )
            await db.commit()

        parser_label = f" ({parsed_doc.parser_used})" if parsed_doc else ""
        return f"\nEmbeddings RAG{parser_label}: {len(doc_chunks)} chunks indexados para búsqueda semántica."
    except Exception as e:
        return f"\nEmbeddings no generados: {e}"


async def _update_doc_status(document_id: str, raw_text: str) -> None:
    """Marca el documento como completado y guarda el contenido parseado."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TenantDocument).where(TenantDocument.id == UUID(document_id))
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


async def _emit_document_processed(
    tenant_id: str, document_id: str, classified: ClassifiedDocument
) -> None:
    """Emite el evento document_processed al bus de eventos."""
    try:
        from app.services.event_bus import emit_event

        async with AsyncSessionLocal() as db:
            await emit_event(
                db=db,
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


async def _classify_with_llm(raw_text: str, rule_result) -> ClassifiedDocument:
    """Clasifica el documento con LLM, con fallback a reglas si falla."""
    llm = get_llm(temperature=0, format_output="json")
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
        if raw_content.startswith("```"):
            raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content)
            raw_content = re.sub(r"\s*```$", "", raw_content)
        if raw_content:
            return ClassifiedDocument(**json.loads(raw_content))
        logger.warning(
            "LLM returned empty response for document classification, using rule fallback"
        )
    except Exception as e:
        logger.warning("LLM classification failed (%s), falling back to rules", e)

    return ClassifiedDocument(
        document_type=rule_result.document_type,
        confidence=max(rule_result.confidence, 0.5),
        key_entities=rule_result.key_entities,
        summary=f"Clasificado por reglas (LLM falló): {rule_result.document_type}",
    )


async def _classify_document_async(tenant_id: str, document_id: str) -> str:
    load_result = await _load_doc_and_extract_text(tenant_id, document_id)
    if isinstance(load_result, str):
        return load_result
    _doc, raw_text, parsed_doc = load_result

    rule_result = classify_by_rules(raw_text)
    logger.info(
        "Clasificación por reglas: %s (confianza=%.0f%%, needs_llm=%s)",
        rule_result.document_type,
        rule_result.confidence * 100,
        rule_result.needs_llm,
    )

    if rule_result.needs_llm:
        classified = await _classify_with_llm(raw_text, rule_result)
    else:
        classified = ClassifiedDocument(
            document_type=rule_result.document_type,
            confidence=rule_result.confidence,
            key_entities=rule_result.key_entities,
            summary=f"Documento clasificado por reglas como {rule_result.document_type}",
        )

    nif_pattern = re.compile(
        r"\b([A-Z][- ]?\d{7}[- ]?[A-Z0-9]|\d{8}[- ]?[A-Z]|[XYZ][- ]?\d{7}[- ]?[A-Z])\b"
    )
    raw_nifs = nif_pattern.findall(raw_text.upper())
    nifs_found = list(dict.fromkeys([n.replace("-", "").replace(" ", "") for n in raw_nifs]))
    client_info = (
        await _link_client_from_nif(tenant_id, nifs_found[0], classified.key_entities)
        if nifs_found
        else ""
    )

    embeddings_info = await _store_embeddings(tenant_id, document_id, raw_text, parsed_doc)
    await _update_doc_status(document_id, raw_text)
    await _emit_document_processed(tenant_id, document_id, classified)

    conf = classified.confidence if classified.confidence is not None else 0.9
    review_note = " ⚠️ Confianza baja, requiere revisión manual." if conf < 0.7 else ""
    return (
        f"Documento clasificado correctamente.\n"
        f"Tipo: {classified.document_type}\n"
        f"Confianza: {conf:.0%}\n"
        f"Resumen: {classified.summary}\n"
        f"Entidades: {json.dumps(classified.key_entities, ensure_ascii=False)}\n"
        f"Acción sugerida: {classified.suggested_action or 'Ninguna'}"
        f"{client_info}{embeddings_info}{review_note}"
    )


@tool
async def search_documents_semantic(tenant_id: str, query: str, limit: int = 5) -> str:
    """
    Busca documentos del tenant usando búsqueda semántica (RAG, coseno en Python).
    Útil para preguntas como "busca contratos de 2024" o "facturas de Acme".

    Args:
        tenant_id: ID del tenant
        query: Texto de búsqueda en lenguaje natural
        limit: Máximo de resultados (por defecto 5)
    """
    return await _search_documents_semantic_async(tenant_id, query, limit)


_SEMANTIC_DISABLED_MSG = (
    "Búsqueda semántica no habilitada en este tenant: la tabla "
    "'document_embeddings' aún no está creada. Como alternativa, usa "
    "list_tenant_documents para listar documentos filtrando por "
    "categoría, o get_document_content para leer un documento concreto."
)


# Re-export del helper para no romper imports antiguos.
from app.agents.agent_tools.semantic_search import (  # noqa: E402
    is_missing_table_or_extension as _is_missing_table_or_extension,
)


async def _search_documents_semantic_async(tenant_id: str, query: str, limit: int) -> str:
    from app.agents.agent_tools.semantic_search import (
        cosine_topk,
        similarity_from_distance,
    )
    from app.db.base import AsyncSessionLocal

    try:
        embedder = get_embedder()
        if not embedder:
            return "Error: No hay proveedor de embeddings configurado."

        query_vector = await embedder.aembed_query(query)

        async with AsyncSessionLocal() as db:
            scored = await cosine_topk(
                db,
                tenant_id=tenant_id,
                query_vector=query_vector,
                top_k=limit,
            )

            if not scored:
                return f"No se encontraron documentos relevantes para: '{query}'"

            lines = []
            for emb, distance in scored:
                similarity = similarity_from_distance(distance)
                snippet = emb.text_content[:200].replace("\n", " ")
                lines.append(
                    f"- Doc ID: {emb.document_id} | Relevancia: {similarity:.0%} | {snippet}..."
                )

            return f"Resultados de búsqueda semántica ({len(scored)}):\n" + "\n".join(lines)
    except Exception as e:
        if _is_missing_table_or_extension(e):
            return _SEMANTIC_DISABLED_MSG
        return f"Error en búsqueda semántica: {e}"


# ─── Lista de herramientas ────────────────────────────────────────────────────

tools = [
    classify_document,
    import_invoice_document,
    search_documents_semantic,
    create_document,
    list_tenant_documents,
    update_existing_document,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
]


# Defensa multi-tenant: envolver tools para forzar tenant_id del ContextVar
from app.agents.tenant_context import isolated as _isolated

tools = _isolated(tools)
