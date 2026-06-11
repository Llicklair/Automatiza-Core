"""Rutas para gestión documental: upload y listado de documentos del tenant."""

import logging
import os
import uuid
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.documents import (
    ContractBodyHtmlIn,
    ContractPreviewHtmlOut,
    ContractTemplateOut,
    DocumentOut,
    ImportDBOut,
    ScanResultOut,
    SemanticSearchHit,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.documents import service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/search", response_model=list[SemanticSearchHit])
async def search_documents(
    q: str,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Búsqueda semántica (RAG, coseno en Python) sobre los documentos del tenant.

    Devuelve los fragmentos más relevantes a la consulta `q`, con su documento
    de origen, página y puntuación de similitud [0-1].
    """
    from app.agents.agent_tools.semantic_search import (
        cosine_topk,
        is_missing_table_or_extension,
        similarity_from_distance,
    )
    from app.core.llm_factory import get_embedder
    from app.db.models.tenant import TenantDocument

    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="La consulta no puede estar vacía")

    embedder = get_embedder()
    if not embedder:
        raise HTTPException(
            status_code=503, detail="No hay proveedor de embeddings configurado"
        )

    query_vector = await embedder.aembed_query(query)
    try:
        scored = await cosine_topk(
            db,
            tenant_id=str(current_user.tenant_id),
            query_vector=query_vector,
            top_k=max(1, min(limit, 20)),
        )
    except Exception as exc:  # tabla aún no creada en este tenant → sin resultados
        if is_missing_table_or_extension(exc):
            return []
        raise

    if not scored:
        return []

    # Nombres de archivo en una sola consulta (evita N+1). Sólo IDs que sean
    # UUID válidos — document_id se almacena como texto y podría traer datos
    # legacy no-UUID que romperían el filtro tipado contra TenantDocument.id.
    import uuid as _uuid

    from sqlalchemy import select as _select

    valid_ids = []
    for emb, _ in scored:
        try:
            valid_ids.append(_uuid.UUID(str(emb.document_id)))
        except (ValueError, TypeError):
            continue
    names: dict[str, str] = {}
    if valid_ids:
        names_q = await db.execute(
            _select(TenantDocument.id, TenantDocument.file_name).where(
                TenantDocument.id.in_(valid_ids)
            )
        )
        names = {str(row.id): row.file_name for row in names_q.all()}

    return [
        SemanticSearchHit(
            document_id=str(emb.document_id),
            file_name=names.get(str(emb.document_id)),
            chunk_index=emb.chunk_index,
            text=(emb.text_content or "")[:500],
            page_number=emb.page_number,
            element_type=emb.element_type,
            similarity=round(similarity_from_distance(dist), 4),
        )
        for emb, dist in scored
    ]


@limiter.limit("30/minute")
@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    category: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sube un archivo (PDF, imagen, DOCX...) para que un agente lo procese."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Archivo sin nombre")

    contents = await file.read()
    try:
        doc = await svc.upload_single(
            file.filename,
            contents,
            file.content_type,
            current_user.tenant_id,
            current_user.id,
            db,
            category,
        )
    except ValueError as e:
        code = 413 if "grande" in str(e) else 400
        raise HTTPException(status_code=code, detail=str(e))
    return doc


@limiter.limit("30/minute")
@router.post("/scan", response_model=list[ScanResultOut])
async def scan_documents(
    request: Request,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Escaner inteligente: sube archivos y los clasifica automaticamente."""
    results: list[ScanResultOut] = []

    for file in files:
        if not file.filename:
            continue
        contents = await file.read()

        # Si es ZIP, descomprimir y escanear cada archivo interno
        if file.filename.lower().endswith(".zip"):
            try:
                entries = svc.extract_zip_entries(contents)
            except zipfile.BadZipFile:
                results.append(
                    ScanResultOut(
                        document=DocumentOut(
                            id=uuid.uuid4(),
                            file_name=file.filename,
                            file_type=None,
                            file_size=len(contents),
                            status="failed",
                            parsed_content=None,
                            category="otros",
                            created_at=__import__("datetime").datetime.now(
                                __import__("datetime").UTC
                            ),
                            processed_at=None,
                            task_id=None,
                        ),
                        auto_category="otros",
                        message=f"Error al descomprimir '{file.filename}'. Verifica que sea un ZIP valido.",
                    )
                )
                continue
            for name, data, mime in entries:
                doc, cat = await svc.scan_single(
                    name,
                    data,
                    mime,
                    current_user.tenant_id,
                    current_user.id,
                    db,
                )
                results.append(
                    ScanResultOut(
                        document=DocumentOut.model_validate(doc),
                        auto_category=cat,
                        message=f"Clasificado como '{cat}'. La IA refinara la categoria.",
                    )
                )
        else:
            doc, cat = await svc.scan_single(
                file.filename,
                contents,
                file.content_type,
                current_user.tenant_id,
                current_user.id,
                db,
            )
            results.append(
                ScanResultOut(
                    document=DocumentOut.model_validate(doc),
                    auto_category=cat,
                    message=f"Clasificado como '{cat}'. La IA refinara la categoria.",
                )
            )
    return results


@limiter.limit("30/minute")
@router.post("/bulk", response_model=list[DocumentOut])
async def upload_bulk_documents(
    request: Request,
    file: UploadFile = File(...),
    category: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sube un archivo ZIP y extrae multiples documentos para procesarlos en lote."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="El archivo masivo debe ser un ZIP")

    contents = await file.read()
    try:
        docs = await svc.upload_bulk(
            contents,
            current_user.tenant_id,
            current_user.id,
            db,
            category,
        )
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="El archivo ZIP esta corrupto")
    return docs


@limiter.limit("30/minute")
@router.get("/export")
async def export_documents(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta todos los documentos del tenant como un archivo ZIP."""
    zip_bytes = await svc.export_all(current_user.tenant_id, db)

    import io

    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="documentos_export.zip"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@limiter.limit("30/minute")
@router.get("", response_model=list[DocumentOut])
async def list_documents(
    request: Request,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos los documentos subidos por el tenant."""
    return await svc.list_documents(current_user.tenant_id, db, category)


@limiter.limit("30/minute")
@router.delete("/{document_id}", status_code=200)
async def delete_document(
    request: Request,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina un documento: borra archivo de disco y registro de BD."""
    deleted = await svc.delete_document(document_id, current_user.tenant_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return {"status": "deleted", "id": str(document_id)}


@limiter.limit("30/minute")
@router.get("/{document_id}/download")
async def download_document(
    request: Request,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descarga un documento del sistema directamente desde disco."""
    doc = await svc.get_document(document_id, current_user.tenant_id, db)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    try:
        file_path = await svc.prepare_download(doc, current_user.tenant_id, db)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    media_type = doc.file_type or "application/octet-stream"
    safe_filename = doc.file_name.replace('"', "_") if doc.file_name else f"documento_{document_id}"
    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@limiter.limit("30/minute")
@router.patch("/{document_id}/content", response_model=DocumentOut)
async def update_document_content(
    request: Request,
    document_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza el contenido textual de un documento existente (TXT/JSON)."""
    doc = await svc.get_document(document_id, current_user.tenant_id, db)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    new_content: str = body.get("content", "")
    append_mode: bool = body.get("append", False)
    if not new_content:
        raise HTTPException(status_code=400, detail="El campo 'content' es obligatorio")

    if doc.file_type and "pdf" in doc.file_type.lower():
        raise HTTPException(
            status_code=400,
            detail="No se puede modificar directamente un PDF. Modifica los datos originales y regenera el PDF.",
        )

    try:
        doc = await svc.update_content(doc, new_content, append_mode, db)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Error escribiendo archivo: {e}")
    return doc


@limiter.limit("30/minute")
@router.get("/by-category/{category}", response_model=list[DocumentOut])
async def list_documents_by_category(
    request: Request,
    category: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista documentos filtrando por categoria."""
    return await svc.list_documents(current_user.tenant_id, db, category)


# ── Plantillas de contrato ────────────────────────────────────────────────────


@limiter.limit("30/minute")
@router.post("/contract-templates/upload", response_model=ContractTemplateOut, status_code=201)
async def upload_contract_template(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sube una plantilla .docx de contrato."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Archivo sin nombre")

    contents = await file.read()
    try:
        doc = await svc.upload_contract_template(
            file.filename,
            contents,
            file.content_type,
            current_user.tenant_id,
            current_user.id,
            db,
        )
    except ValueError as e:
        code = 413 if "grande" in str(e) else 400
        raise HTTPException(status_code=code, detail=str(e))
    return doc


@limiter.limit("30/minute")
@router.get("/contract-templates", response_model=list[ContractTemplateOut])
async def list_contract_templates(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las plantillas .docx de contrato."""
    return await svc.list_contract_templates(current_user.tenant_id, db)


@limiter.limit("60/minute")
@router.get("/contract-templates/{document_id}/preview-html", response_model=ContractPreviewHtmlOut)
async def preview_contract_template_html(
    request: Request,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Vista previa HTML + variables {{...}} detectadas."""
    doc = await svc.get_contract_template(document_id, current_user.tenant_id, db)
    if not doc:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    try:
        file_path = svc.validate_template_on_disk(doc)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        data = svc.preview_contract_html(file_path)
    except ImportError:
        raise HTTPException(
            status_code=501, detail="mammoth no instalado. Ejecuta: pip install mammoth"
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archivo de plantilla no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("preview_contract_template_html: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generando vista previa: {e}")
    return ContractPreviewHtmlOut(**data)


@limiter.limit("20/minute")
@router.put("/contract-templates/{document_id}/body-html")
async def save_contract_template_body_html(
    request: Request,
    document_id: uuid.UUID,
    body: ContractBodyHtmlIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Guarda el HTML editado en el navegador como .docx."""
    doc = await svc.get_contract_template(document_id, current_user.tenant_id, db)
    if not doc:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")

    try:
        new_size = await svc.save_contract_html_and_update(body.html, doc, db)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError:
        raise HTTPException(
            status_code=501, detail="htmldocx no instalado. Ejecuta: pip install htmldocx"
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except OSError as e:
        logger.error("save_contract_template_body_html: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"No se pudo guardar el archivo: {e}")

    return {"status": "saved", "file_size": new_size}


@limiter.limit("10/minute")
@router.post("/contract-templates/{document_id}/generate")
async def generate_contract(
    request: Request,
    document_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rellena una plantilla .docx con datos del cliente o empleado."""
    doc = await svc.get_contract_template(document_id, current_user.tenant_id, db)
    if not doc:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    try:
        svc.validate_template_on_disk(doc)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        docx_bytes, filename = await svc.generate_contract_from_template(
            doc,
            entity_type,
            entity_id,
            current_user.tenant_id,
            db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError:
        raise HTTPException(
            status_code=501, detail="docxtpl no instalado. Ejecuta: pip install docxtpl"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando contrato: {e}")

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@limiter.limit("30/minute")
@router.delete("/contract-templates/{document_id}", status_code=200)
async def delete_contract_template(
    request: Request,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina una plantilla de contrato del tenant."""
    deleted = await svc.delete_contract_template(document_id, current_user.tenant_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return {"status": "deleted", "id": str(document_id)}


# ── Importar bases de datos ──────────────────────────────────────────────────


@limiter.limit("30/minute")
@router.post("/import-db", response_model=list[ImportDBOut])
async def import_database(
    request: Request,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Importa archivos tabulares (.csv, .xlsx, .json) y lanza la IA para clasificarlos."""
    results: list[ImportDBOut] = []

    for file in files:
        if not file.filename:
            continue

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in (".csv", ".xlsx", ".xls", ".json", ".ods"):
            results.append(
                ImportDBOut(
                    document_id=uuid.uuid4(),
                    file_name=file.filename,
                    rows_detected=0,
                    columns=[],
                    category="otros",
                    task_id=None,
                    message=f"Formato '{ext}' no soportado. Usa CSV, XLSX, JSON u ODS.",
                )
            )
            continue

        contents = await file.read()
        doc, columns, row_count, auto_cat, task_id = await svc.import_tabular_file(
            file.filename,
            contents,
            file.content_type,
            current_user.tenant_id,
            current_user.id,
            db,
        )
        results.append(
            ImportDBOut(
                document_id=doc.id,
                file_name=file.filename,
                rows_detected=row_count,
                columns=columns[:20],
                category=auto_cat,
                task_id=task_id,
                message=f"{row_count} filas detectadas -> carpeta '{auto_cat}'. La IA esta procesando los datos.",
            )
        )

    return results


@limiter.limit("30/minute")
@router.post("/{document_id}/erp-import/preview")
async def erp_import_preview(
    request: Request,
    document_id: uuid.UUID,
    payload: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Previsualiza el mapeo de un archivo tabular ya subido → entidades del ERP.

    Body opcional: {"target": "productos"|"clientes"|"empleados"}. Si falta, se
    detecta por las columnas. NO crea nada.
    """
    from app.services.documents.erp_import import preview_import

    target = (payload or {}).get("target")
    try:
        return await preview_import(db, current_user.tenant_id, document_id, target)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@limiter.limit("10/minute")
@router.post("/{document_id}/erp-import")
async def erp_import_apply(
    request: Request,
    document_id: uuid.UUID,
    payload: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea en el ERP los registros del archivo tabular ya revisado.

    Body: {"target": "productos"|"clientes"|"empleados"}.
    """
    from app.services.documents.erp_import import apply_import

    target = (payload or {}).get("target")
    try:
        return await apply_import(db, current_user.tenant_id, document_id, target)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=422, detail=str(e))
