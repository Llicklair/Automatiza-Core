"""
Agente de Documentos — Fase 2.

Flujo:
  1. Recibe un documento (PDF/imagen) adjunto o URL
  2. Clasifica el tipo: factura recibida | contrato | extracto bancario | otro
  3. Extrae datos con OCR (Azure Form Recognizer) → siempre estructurado
  4. Valida los datos extraídos determinísticamente
  5. Archiva en Google Drive / OneDrive (Fase 3) o devuelve para revisión
  6. Registra todo en audit log
"""
import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm_factory import get_llm, get_embedder
from app.core.prompt_sanitizer import sanitize_user_input
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from app.core.config import settings

# ─── Tipos de documento ───────────────────────────────────────────────────────

class DocumentType(str):
    INVOICE_RECEIVED = "factura_recibida"
    CONTRACT         = "contrato"
    BANK_STATEMENT   = "extracto_bancario"
    PAYROLL          = "nomina"
    OTHER            = "otro"


class ClassifiedDocument(BaseModel):
    document_type: str
    confidence: float | None = 0.9  # Default if LLM fails to provide
    language: str = "es"
    requires_action: bool = False
    suggested_action: str | None = None
    key_entities: dict = Field(default_factory=dict)
    summary: str = ""


# ─── LLM para clasificación y resumen ────────────────────────────────────────

CLASSIFICATION_PROMPT = """Eres un experto analista de documentos. Se te pasará el texto extraído de un documento real.
Tu tarea es leer el documento y extraer la información solicitada basándote ÚNICAMENTE en su contenido.

Devuelve ESTRICTAMENTE un objeto JSON siguiendo esta estructura de ejemplo, pero RELLENANDO los datos con la información REAL del documento:

{
  "document_type": "factura_recibida|contrato|extracto_bancario|nomina|otro",
  "confidence": 0.95,
  "language": "es",
  "requires_action": true,
  "suggested_action": "Breve sugerencia de qué hacer con este documento",
  "key_entities": {
    "emisor": "Nombre completo de quien emite el documento",
    "receptor": "Nombre completo de quien lo recibe",
    "importe": "Cantidad con moneda si la hay",
    "fecha": "Fecha del documento",
    "numero_referencia": "Número de factura, expediente o referencia única"
  },
  "summary": "Resumen conciso en una sola frase de lo que trata el documento"
}

Si un dato no aparece en el texto, pon null o vacío. NO INVENTES DATOS NI COPIES EL EJEMPLO. Extrae la información real del texto proporcionado.

REGLAS:
1. Si es factura recibida: requires_action=true, suggested_action="Registrar gasto + IVA soportado"
2. Si es contrato: requires_action=true, suggested_action="Revisar cláusulas y fecha de vencimiento"
3. Si es extracto: requires_action=false, suggested_action="Conciliar con facturas pendientes"
4. NUNCA inventes importes ni fechas que no estén en el texto."""


def _get_llm():
    return get_llm(temperature=0, format_output="json")


# ─── Función principal del agente ────────────────────────────────────────────

async def _extract_contact_from_text(text: str, nif: str, llm) -> dict:
    """Extrae datos básicos del contacto desde el documento usando el LLM."""
    from langchain_core.messages import HumanMessage, SystemMessage
    prompt = f"""Extrae los datos de la entidad con NIF/CIF {nif} que aparece en este documento.
Devuelve un JSON estricto con las siguientes claves:
- name: nombre completo de la empresa o persona (obligatorio)
- email: correo electrónico (si aparece, si no null)
- address: dirección completa (si aparece, si no null)
- city: ciudad (si aparece, si no null)
- postalCode: código postal (si aparece, si no null)

Documento:
{text[:4000]}"""
    try:
        response = await llm.ainvoke([
            SystemMessage(content="Eres un extractor de datos de entidades. Devuelve SOLO JSON válido."),
            HumanMessage(content=prompt)
        ])
        import json
        data = json.loads(response.content)
        return {
            "name": data.get("name") or "Contacto Desconocido",
            "vatnumber": nif,
            "email": data.get("email"),
            "address": data.get("address"),
            "city": data.get("city"),
            "postalCode": data.get("postalCode"),
            "isperson": len(nif) == 9 and not nif[0].isalpha() or (nif and nif[0] in ['X', 'Y', 'Z']),
            "clientRecord": 1,
        }
    except Exception:
        return {"name": f"Contacto {nif}", "vatnumber": nif, "clientRecord": 1}


class DocumentsAgentResult(BaseModel):
    success: bool
    document_type: str | None = None
    extracted_data: dict | None = None
    classified: ClassifiedDocument | None = None
    requires_review: bool = False
    holded_upload: dict | None = None
    error: str | None = None


async def run_documents_agent(
    user_intent: str,
    file_bytes: bytes | None = None,
    file_content_type: str = "application/pdf",
    azure_endpoint: str | None = None,
    azure_api_key:  str | None = None,
    holded_api_key: str | None = None,
    holded_file_name: str | None = None,
    holded_file_content_type: str | None = None,
    tenant_id: str | None = None,
    document_id: str | None = None,
) -> DocumentsAgentResult:
    """
    Ejecuta el agente de documentos:
    1. Si hay archivo → OCR con Azure para extraer texto estructurado
    2. Clasificación y resumen con LLM (sobre texto anonimizado)
    3. Devuelve datos estructurados para archivar o revisar
    """
    extracted_data: dict = {}
    raw_text: str = ""

    # ── PASO 1a: OCR con Azure (si está configurado) ──────────────────────
    if file_bytes and azure_endpoint and azure_api_key and azure_api_key != "DEMO_AZURE_KEY":
        from app.integrations.azure_forms import AzureFormsClient
        client = AzureFormsClient(endpoint=azure_endpoint, api_key=azure_api_key)
        try:
            result = await client.analyze_invoice(file_bytes, content_type=file_content_type)
            extracted_data = AzureFormsClient.extract_invoice_fields(result)
        except Exception as e:
            try:
                result = await client.analyze_document(file_bytes, content_type=file_content_type)
                extracted_data = {"raw_content": result.get("content", "")[:3000]}
            except Exception:
                return DocumentsAgentResult(
                    success=False,
                    error=f"Error en OCR: {str(e)}. Verifica la integración con Azure."
                )
        finally:
            await client.close()

    # ── PASO 1b: Extracción de texto local con pypdf (fallback sin Azure) ──
    if file_bytes and not extracted_data:
        try:
            import io

            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for page in reader.pages[:8]:  # Máx 8 páginas para no saturar el LLM
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(text)
            raw_text = "\n".join(pages_text)[:5000]
            if raw_text.strip():
                extracted_data = {"raw_content": raw_text}
        except Exception as e:
            logger.warning("Error al extraer texto del PDF con pypdf: %s", e)
            # Texto plano (txt, csv, etc.)
            try:
                raw_text = file_bytes.decode("utf-8", errors="ignore")[:5000]
                if raw_text.strip():
                    extracted_data = {"raw_content": raw_text}
            except Exception as e2:
                logger.warning("Error al decodificar archivo como texto plano: %s", e2)

    # ── PASO 2: Construir texto para el LLM ───────────────────────────────
    if extracted_data:
        context_text = (
            extracted_data.get("raw_content")
            or json.dumps(extracted_data, ensure_ascii=False)
        )
        context_text = context_text[:4500]
    else:
        context_text = f"Instrucción del usuario: {user_intent}"


    # ── PASO 3: Clasificación + resumen con LLM ────────────────────────────
    llm = _get_llm()
    messages = [
        SystemMessage(content=CLASSIFICATION_PROMPT),
        HumanMessage(content=f"Clasifica este documento:\n\n{sanitize_user_input(context_text)}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        data_dict = json.loads(response.content)
        classified = ClassifiedDocument(**data_dict)
    except Exception as e:
        return DocumentsAgentResult(
            success=False,
            error=f"Error en clasificación: {str(e)}",
            extracted_data=extracted_data,
        )

    # ── PASO 4: Validación determinista básica ────────────────────────────
    _conf = classified.confidence if classified.confidence is not None else 0.9
    requires_review = _conf < 0.7 or classified.document_type == "otro"

    # ── PASO 5: Guardar contacto LOCAL (siempre) + Holded si está activo ──
    holded_upload_result: dict = {}

    # Extraer NIFs/CIFs del texto del documento con regex
    import re
    source_text = raw_text or context_text or ""
    nif_pattern_relaxed = re.compile(
        r"\b([A-Z][- ]?\d{7}[- ]?[A-Z0-9]|\d{8}[- ]?[A-Z]|[XYZ][- ]?\d{7}[- ]?[A-Z])\b"
    )
    raw_nifs = nif_pattern_relaxed.findall(source_text.upper())
    nifs_found = list(dict.fromkeys([n.replace("-", "").replace(" ", "") for n in raw_nifs]))

    if file_bytes and nifs_found:
        primary_nif = nifs_found[0]

        # ── 5a: Siempre upsert en BD local ────────────────────────────────
        if tenant_id:
            try:
                import uuid as _uuid

                from sqlalchemy import select

                from app.db.base import AsyncSessionLocal
                from app.db.models.models import Client

                contact_data_for_local = await _extract_contact_from_text(source_text, primary_nif, llm)

                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Client).where(
                            Client.tenant_id == _uuid.UUID(tenant_id),
                            Client.nif == primary_nif,
                        )
                    )
                    local_client = result.scalar_one_or_none()

                    if not local_client:
                        local_client = Client(
                            tenant_id=_uuid.UUID(tenant_id),
                            nif=primary_nif,
                            name=contact_data_for_local.get("name") or f"Contacto {primary_nif}",
                            email=contact_data_for_local.get("email"),
                            address=contact_data_for_local.get("address"),
                            city=contact_data_for_local.get("city"),
                            postal_code=contact_data_for_local.get("postalCode"),
                            client_type="supplier",  # Por defecto proveedor (factura recibida)
                        )
                        db.add(local_client)
                        await db.commit()
                        await db.refresh(local_client)
                    local_client_id = local_client.id

            except Exception as e:
                local_client_id = None
                print(f"[documents_agent] Error guardando cliente local: {e}")
        else:
            local_client_id = None

        # ── 5b: Sincronizar con Holded si está configurado (opcional) ─────
        if file_bytes and holded_api_key:
            try:
                import uuid as _uuid

                from sqlalchemy import select

                from app.db.base import AsyncSessionLocal
                from app.db.models.models import Client
                from app.integrations.holded import HoldedClient

                holded = HoldedClient(api_key=holded_api_key)
                matched_contact = None
                matched_nif = None

                for nif in nifs_found[:5]:
                    contact = await holded.get_contact_by_nif(nif)
                    if contact:
                        matched_contact = contact
                        matched_nif = nif
                        break

                if matched_contact:
                    holded_contact_id = matched_contact["id"]
                    contact_created_in_holded = False
                else:
                    # Crear en Holded usando los datos ya extraídos
                    contact_data_holded = await _extract_contact_from_text(source_text, primary_nif, llm)
                    try:
                        new_contact = await holded.create_contact(contact_data_holded)
                        holded_contact_id = new_contact.get("id") or new_contact.get("contactId", "")
                        contact_created_in_holded = bool(holded_contact_id)
                        matched_nif = primary_nif
                    except Exception as ce:
                        holded_contact_id = None
                        contact_created_in_holded = False
                        holded_upload_result = {"uploaded": False, "reason": f"Error creando contacto en Holded: {ce}"}

                # Actualizar holded_id en el cliente local
                if holded_contact_id and tenant_id and local_client_id:
                    try:
                        async with AsyncSessionLocal() as db:
                            result = await db.execute(
                                select(Client).where(Client.id == local_client_id)
                            )
                            cl = result.scalar_one_or_none()
                            if cl and not cl.holded_id:
                                cl.holded_id = holded_contact_id
                                await db.commit()
                    except Exception as e:
                        logger.warning("Error al actualizar holded_id en cliente local %s: %s", local_client_id, e)

                # Subir adjunto a Holded
                if holded_contact_id and file_bytes:
                    fn = holded_file_name or "documento.pdf"
                    ct = holded_file_content_type or "application/pdf"
                    try:
                        await holded.upload_contact_attachment(
                            contact_id=holded_contact_id,
                            file_bytes=file_bytes,
                            file_name=fn,
                            content_type=ct,
                        )
                        holded_upload_result = {
                            "uploaded": True,
                            "contact_id": holded_contact_id,
                            "nif": matched_nif or primary_nif,
                            "contact_created": contact_created_in_holded,
                        }
                    except Exception as ae:
                        holded_upload_result = {"uploaded": False, "reason": f"Error adjuntando en Holded: {ae}"}

                await holded.close()

            except Exception as e:
                holded_upload_result = {"uploaded": False, "reason": str(e)}

    elif file_bytes and not nifs_found:
        holded_upload_result = {"uploaded": False, "reason": "No se encontraron NIFs/CIFs en el documento"}

    # ── PASO 6: Generar e Insertar Embeddings para RAG ────────────────────
    if document_id and tenant_id:
        source_text = raw_text or context_text or ""
        if source_text:
            try:
                import uuid

                from app.db.base import AsyncSessionLocal
                from app.db.models.embeddings import DocumentEmbedding

                embedder = get_embedder()
                if embedder is None:
                    raise RuntimeError("No hay proveedor de embeddings configurado")

                chunk_size = 1500
                chunks = []
                for i in range(0, len(source_text), chunk_size):
                    chunks.append(source_text[i:i+chunk_size])
                
                # Asynchronously generate embeddings
                # Note: 'aembed_documents' might raise an error if nomic-embed-text model is not pulled yet
                embeddings_vectors = await embedder.aembed_documents(chunks)
                
                async with AsyncSessionLocal() as db:
                    for i, (chunk, vector) in enumerate(zip(chunks, embeddings_vectors)):
                        new_emb = DocumentEmbedding(
                            document_id=document_id,
                            tenant_id=uuid.UUID(tenant_id),
                            chunk_index=str(i),
                            text_content=chunk,
                            embedding=vector
                        )
                        db.add(new_emb)
                    await db.commit()
            except Exception as e:
                import traceback
                traceback.print_exc()
                # Log but do not fail the task if RAG embedding fails
                print(f"Error generating Document Embeddings: {e}")

    # ── PASO 7: Emitir evento de dominio ──
    try:
        from app.services.event_bus import emit_event
        from app.db.base import AsyncSessionLocal
        import uuid as _uuid
        async with AsyncSessionLocal() as db_ev:
            await emit_event(
                db=db_ev,
                tenant_id=_uuid.UUID(tenant_id) if tenant_id else None,
                user_id=None,
                event_name="document_processed",
                context={
                    "document_id": document_id,
                    "document_type": classified.document_type,
                    "file_name": holded_file_name,
                    "key_entities": classified.key_entities,
                    "requires_review": requires_review
                }
            )
    except Exception as e:
        logger.warning("Error al emitir evento document_processed para documento %s: %s", document_id, e)

    return DocumentsAgentResult(
        success=True,
        document_type=classified.document_type,
        extracted_data=extracted_data,
        classified=classified,
        requires_review=requires_review,
        holded_upload=holded_upload_result if holded_upload_result else None,
    )
