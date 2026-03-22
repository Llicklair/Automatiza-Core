"""Rutas para gestión documental: upload y listado de documentos del tenant."""
import logging
import os
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Task, Tenant, TenantDocument, User

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads"))


# ─── Schemas ──────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    file_name: str
    file_type: str | None
    file_size: int
    status: str
    parsed_content: str | None
    category: str | None
    created_at: datetime
    processed_at: datetime | None
    task_id: uuid.UUID | None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    category: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sube un archivo (PDF, imagen, DOCX…) para que un agente lo procese."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Archivo sin nombre")

    # Validar extensión permitida
    ALLOWED_EXTENSIONS = {
        ".pdf", ".doc", ".docx", ".odt", ".txt", ".md",
        ".xlsx", ".xls", ".csv", ".ods", ".json",
        ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif",
        ".eml", ".msg", ".zip",
    }
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Extensión '{ext}' no permitida")

    # Leer con límite de tamaño (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx. 50MB)")

    # Guardar a disco
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        f.write(contents)

    doc = TenantDocument(
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.id,
        file_name=file.filename,
        file_type=file.content_type,
        file_path=file_path,
        file_size=len(contents),
        category=category,
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Disparar tarea de procesamiento en el orquestador
    try:
        from app.db.models.models import Task
        from app.services.task_dispatch import dispatch_orchestrator

        task = Task(
            tenant_id=current_user.tenant_id,
            created_by=current_user.id,
            domain="documents",
            user_intent=f"Procesar documento adjunto: {file.filename}",
            status="pending",
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        doc.task_id = task.id
        doc.status = "processing"
        await db.commit()
        await db.refresh(doc)

        await dispatch_orchestrator(str(task.id))
    except Exception as e:
        logger.warning("Orchestrator dispatch falló para doc %s: %s", doc.id, e)

    return doc


# ── Mapeo rápido extensión/MIME → categoría ─────────────────────────────────
_EXT_CATEGORY_MAP: dict[str, str] = {
    ".xlsx": "excels", ".xls": "excels", ".csv": "excels", ".ods": "excels",
    ".pdf": "facturas",   # default para PDF; la IA refinará después
    ".docx": "otros", ".doc": "otros", ".odt": "otros",
    ".png": "otros", ".jpg": "otros", ".jpeg": "otros", ".webp": "otros",
    ".gif": "otros", ".bmp": "otros", ".tiff": "otros", ".tif": "otros",
    ".txt": "otros", ".md": "otros",
    ".eml": "correos", ".msg": "correos",
}

_MIME_CATEGORY_MAP: dict[str, str] = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excels",
    "application/vnd.ms-excel": "excels",
    "text/csv": "excels",
    "application/pdf": "facturas",
    "message/rfc822": "correos",
    "application/vnd.ms-outlook": "correos",
}


def _auto_classify_category(filename: str, content_type: str | None) -> str:
    """Clasifica la categoría inicial de un archivo por extensión y MIME."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in _EXT_CATEGORY_MAP:
        return _EXT_CATEGORY_MAP[ext]
    if content_type and content_type in _MIME_CATEGORY_MAP:
        return _MIME_CATEGORY_MAP[content_type]
    if content_type and content_type.startswith("image/"):
        return "otros"  # imágenes → OCR decidirá
    return "otros"


class ScanResultOut(BaseModel):
    document: DocumentOut
    auto_category: str
    message: str


@router.post("/scan", response_model=list[ScanResultOut])
async def scan_documents(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Escáner inteligente: sube uno o más archivos y los clasifica automáticamente.
    1. Clasifica por extensión/MIME (rápido)
    2. Lanza el orchestrator para clasificación IA profunda (async)
    La IA puede reclasificar el documento a otra carpeta después del análisis.
    """
    results = []
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    async def _scan_single(filename: str, contents: bytes, content_type: str | None):
        """Procesa un único archivo: guardar, clasificar, lanzar IA."""
        ext = os.path.splitext(filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        with open(file_path, "wb") as f:
            f.write(contents)

        auto_cat = _auto_classify_category(filename, content_type)

        doc = TenantDocument(
            tenant_id=current_user.tenant_id,
            uploaded_by=current_user.id,
            file_name=filename,
            file_type=content_type,
            file_path=file_path,
            file_size=len(contents),
            category=auto_cat,
            status="uploaded",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        try:
            from app.services.task_dispatch import dispatch_orchestrator

            task = Task(
                tenant_id=current_user.tenant_id,
                created_by=current_user.id,
                domain="documents",
                user_intent=f"Escanear y clasificar documento: {filename}",
                status="pending",
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)

            doc.task_id = task.id
            doc.status = "processing"
            await db.commit()
            await db.refresh(doc)

            await dispatch_orchestrator(str(task.id))
        except Exception as e:
            logger.warning("Orchestrator dispatch falló en scan para doc %s: %s", doc.id, e)

        results.append(ScanResultOut(
            document=doc,
            auto_category=auto_cat,
            message=f"Clasificado como '{auto_cat}'. La IA refinará la categoría.",
        ))

    for file in files:
        if not file.filename:
            continue

        contents = await file.read()

        # Si es ZIP, descomprimir y escanear cada archivo interno
        if file.filename.lower().endswith(".zip"):
            import io
            import mimetypes
            import zipfile

            try:
                with zipfile.ZipFile(io.BytesIO(contents)) as z:
                    for info in z.infolist():
                        if info.is_dir() or info.filename.startswith("__MACOSX") or info.filename.startswith("."):
                            continue
                        original_name = os.path.basename(info.filename)
                        if not original_name:
                            continue
                        extracted_data = z.read(info.filename)
                        mime_type, _ = mimetypes.guess_type(original_name)
                        await _scan_single(original_name, extracted_data, mime_type)
            except Exception:
                results.append(ScanResultOut(
                    document=TenantDocument(
                        id=uuid.uuid4(), tenant_id=current_user.tenant_id,
                        file_name=file.filename, file_path="", file_size=len(contents),
                        status="failed", category="otros",
                    ),
                    auto_category="otros",
                    message=f"Error al descomprimir '{file.filename}'. Verifica que sea un ZIP válido.",
                ))
        else:
            await _scan_single(file.filename, contents, file.content_type)

    return results


@router.post("/bulk", response_model=list[DocumentOut])
async def upload_bulk_documents(
    file: UploadFile = File(...),
    category: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sube un archivo ZIP y extrae múltiples documentos para procesarlos en lote."""
    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail="El archivo masivo debe ser un ZIP")

    import io
    import zipfile

    # Guardar ZIP en memoria
    contents = await file.read()
    
    docs_created = []
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as z:
            for info in z.infolist():
                if info.is_dir() or info.filename.startswith('__MACOSX') or info.filename.startswith('.'):
                    continue

                # Extraer archivo
                extracted_data = z.read(info.filename)
                
                # Nombre original base (sin directorios)
                original_name = os.path.basename(info.filename)
                if not original_name:
                    continue
                    
                ext = os.path.splitext(original_name)[1]
                unique_name = f"{uuid.uuid4().hex}{ext}"
                file_path = os.path.join(UPLOAD_DIR, unique_name)

                with open(file_path, "wb") as f:
                    f.write(extracted_data)

                # Registrar documento
                import mimetypes
                mime_type, _ = mimetypes.guess_type(original_name)
                
                doc = TenantDocument(
                    tenant_id=current_user.tenant_id,
                    uploaded_by=current_user.id,
                    file_name=original_name,
                    file_type=mime_type or "application/octet-stream",
                    file_path=file_path,
                    file_size=len(extracted_data),
                    category=category,
                    status="uploaded",
                )
                db.add(doc)
                await db.commit()
                await db.refresh(doc)
                
                # Crear tarea para este documento
                from app.db.models.models import Task
                from app.services.task_dispatch import dispatch_orchestrator

                task = Task(
                    tenant_id=current_user.tenant_id,
                    created_by=current_user.id,
                    domain="documents",
                    user_intent=f"Procesar documento masivo: {original_name}",
                    status="pending",
                )
                db.add(task)
                await db.commit()
                await db.refresh(task)

                doc.task_id = task.id
                doc.status = "processing"
                await db.commit()
                await db.refresh(doc)

                await dispatch_orchestrator(str(task.id))
                
                docs_created.append(doc)
                
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="El archivo ZIP está corrupto o es inválido")

    return docs_created


@router.get("/export")
async def export_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta todos los documentos del tenant como un archivo ZIP."""
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    result = await db.execute(
        select(TenantDocument)
        .where(TenantDocument.tenant_id == current_user.tenant_id)
        .order_by(desc(TenantDocument.created_at))
        .limit(500)
    )
    docs = result.scalars().all()

    zip_buffer = io.BytesIO()
    added_names: set[str] = set()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc in docs:
            if not doc.file_path:
                continue
            normalized = os.path.normpath(doc.file_path)
            if not os.path.exists(normalized):
                continue
            # Deduplicate names inside the ZIP
            base_name = doc.file_name or os.path.basename(normalized)
            base, ext = os.path.splitext(base_name)
            unique_name = base_name
            counter = 1
            while unique_name in added_names:
                unique_name = f"{base}_{counter}{ext}"
                counter += 1
            added_names.add(unique_name)
            zf.write(normalized, unique_name)

    zip_data = zip_buffer.getvalue()
    return StreamingResponse(
        io.BytesIO(zip_data),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="documentos_backup.zip"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos los documentos subidos por el tenant. Permite filtrar por tipo/categoría."""
    query = (
        select(TenantDocument)
        .where(TenantDocument.tenant_id == current_user.tenant_id)
        .order_by(desc(TenantDocument.created_at))
        .limit(50)
    )
    
    if category and category != "all":
        query = query.where(TenantDocument.category == category)
        
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/{document_id}", status_code=200)
async def cancel_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancela o descarta un documento atascado en procesamiento."""
    result = await db.execute(
        select(TenantDocument).where(
            TenantDocument.id == document_id,
            TenantDocument.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    doc.status = "failed"
    await db.commit()
    return {"status": "cancelled", "id": str(document_id)}


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descarga un documento del sistema (PDF, DOCX, etc.) directamente desde disco."""
    result = await db.execute(
        select(TenantDocument).where(
            TenantDocument.id == document_id,
            TenantDocument.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if not doc.file_path:
        raise HTTPException(status_code=404, detail="Este documento no tiene archivo en disco")

    # Normalizar ruta en Windows (barras invertidas → barras normales)
    file_path = os.path.normpath(doc.file_path)

    if not os.path.exists(file_path):
        # Fallback: buscar por nombre en UPLOAD_DIR
        fallback = os.path.join(UPLOAD_DIR, doc.file_name) if doc.file_name else None
        if fallback and os.path.exists(fallback):
            file_path = fallback
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Archivo no disponible en disco: {file_path}"
            )

    # Si es un PDF de factura IA antiguo y no es un PDF real, intentar regenerarlo al vuelo.
    # (Muchos se generaron como texto plano cuando reportlab no estaba instalado en el worker.)
    try:
        is_ai_invoice_pdf = (doc.file_name or "").lower().startswith("factura_ia_") and (
            (doc.file_type or "").lower() == "application/pdf"
        )
        if is_ai_invoice_pdf:
            with open(file_path, "rb") as f:
                header = f.read(5)

            if header != b"%PDF-":
                # Buscar datos originales en la Task ligada
                extracted_data = None
                if doc.task_id:
                    task_result = await db.execute(
                        select(Task).where(
                            Task.id == doc.task_id,
                            Task.tenant_id == current_user.tenant_id,
                        )
                    )
                    task = task_result.scalar_one_or_none()
                    if task and task.agent_results:
                        for r in (task.agent_results or []):
                            if not isinstance(r, dict):
                                continue
                            if r.get("agent") != "billing":
                                continue
                            out = r.get("output") or {}
                            if isinstance(out, dict) and out.get("extracted_data"):
                                extracted_data = out.get("extracted_data")
                                break

                if isinstance(extracted_data, dict):
                    from app.services.pdf_service import generate_invoice_pdf

                    base = float(extracted_data.get("amount_base") or 0)
                    vat_rate = float(extracted_data.get("vat_rate") or 21)
                    tax = round(base * vat_rate / 100, 2)
                    total = round(base + tax, 2)
                    task_id_str = str(doc.task_id) if doc.task_id else ""
                    invoice_number = f"IA-{task_id_str[:8].upper()}" if task_id_str else "IA"

                    # Datos de la empresa (tenant)
                    tenant_result = await db.execute(
                        select(Tenant).where(Tenant.id == current_user.tenant_id)
                    )
                    tenant_obj = tenant_result.scalar_one_or_none()
                    company_name = tenant_obj.name if tenant_obj else "Mi Empresa S.L."
                    company_nif = extracted_data.get("issuer_nif") or (
                        tenant_obj.nif if tenant_obj else "B00000000"
                    )
                    company_address = extracted_data.get("issuer_address") or "Calle Principal, 1 · Madrid"
                    company_email = extracted_data.get("issuer_email") or ""

                    invoice_data = {
                        "number": invoice_number,
                        "date": extracted_data.get("invoice_date") or datetime.now(UTC).strftime("%Y-%m-%d"),
                        "amount_base": base,
                        "tax_amount": tax,
                        "amount_total": total,
                        "client": {
                            "name": extracted_data.get("client_name") or "Cliente",
                            "nif": extracted_data.get("client_nif") or "",
                            "email": "",
                            "address": "",
                        },
                        "company": {
                            "name": company_name,
                            "nif": company_nif,
                            "address": company_address,
                            "phone": "",
                            "email": company_email,
                        },
                        "lines": [
                            {
                                "description": extracted_data.get("concept") or "Servicio",
                                "quantity": 1.0,
                                "unit_price": base,
                                "tax_percentage": vat_rate,
                                "total": total,
                            }
                        ],
                    }
                    if extracted_data.get("notes"):
                        invoice_data["notes"] = extracted_data["notes"]
                    if extracted_data.get("payment_terms") or extracted_data.get("payment_method"):
                        invoice_data["payment_terms"] = extracted_data.get("payment_terms") or extracted_data.get("payment_method")

                    pdf_bytes = generate_invoice_pdf(invoice_data)
                    if pdf_bytes.startswith(b"%PDF-"):
                        with open(file_path, "wb") as f:
                            f.write(pdf_bytes)
                        doc.file_size = len(pdf_bytes)
                        doc.file_type = "application/pdf"
                        doc.processed_at = datetime.now(UTC)
                        doc.status = "completed"
                        await db.commit()
                    else:
                        raise HTTPException(
                            status_code=409,
                            detail="No se pudo regenerar el PDF de la factura IA (bytes inválidos).",
                        )
                else:
                    raise HTTPException(
                        status_code=409,
                        detail="El PDF de factura IA no es válido y no se encontraron datos para regenerarlo.",
                    )
    except HTTPException:
        raise
    except Exception:
        # No bloquear descarga por errores de regeneración; se devolverá el archivo existente.
        pass

    media_type = doc.file_type or "application/octet-stream"
    safe_filename = doc.file_name.replace('"', '_') if doc.file_name else f"documento_{document_id}"

    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.patch("/{document_id}/content", response_model=DocumentOut)
async def update_document_content(
    document_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Actualiza el contenido textual de un documento existente (TXT/JSON).
    Usado por los agentes IA para modificar documentos del escanear.
    body = {"content": "nuevo contenido", "append": false}
    Si 'append' es True, el contenido se adjunta al final en lugar de reemplazar.
    """
    result = await db.execute(
        select(TenantDocument).where(
            TenantDocument.id == document_id,
            TenantDocument.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    new_content: str = body.get("content", "")
    append_mode: bool = body.get("append", False)

    if not new_content:
        raise HTTPException(status_code=400, detail="El campo 'content' es obligatorio")

    # Solo se puede modificar documentos de texto plano
    if doc.file_type and "pdf" in doc.file_type.lower():
        raise HTTPException(
            status_code=400,
            detail="No se puede modificar directamente un PDF. Modifica los datos originales y regenera el PDF."
        )

    # Actualizar el archivo en disco
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            mode = "a" if append_mode else "w"
            with open(doc.file_path, mode, encoding="utf-8") as f:
                if append_mode:
                    f.write(f"\n\n--- Modificacion {datetime.now(UTC).strftime('%d/%m/%Y %H:%M')} ---\n")
                f.write(new_content)
            # Actualizar tamaño
            doc.file_size = os.path.getsize(doc.file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error escribiendo archivo: {e}")
    else:
        # Si no hay archivo en disco, recrearlo
        try:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            file_path = os.path.join(UPLOAD_DIR, doc.file_name or f"doc_{document_id}.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            doc.file_path = file_path
            doc.file_size = len(new_content.encode())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creando archivo: {e}")

    # Actualizar parsed_content en BD para RAG
    if append_mode:
        doc.parsed_content = (doc.parsed_content or "") + "\n" + new_content
    else:
        doc.parsed_content = new_content

    doc.processed_at = datetime.now(UTC)
    doc.status = "completed"
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/by-category/{category}", response_model=list[DocumentOut])
async def list_documents_by_category(
    category: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista documentos filtrando por categoría. Util para que la IA identifique documentos a modificar."""
    result = await db.execute(
        select(TenantDocument)
        .where(
            TenantDocument.tenant_id == current_user.tenant_id,
            TenantDocument.category == category,
        )
        .order_by(desc(TenantDocument.created_at))
        .limit(20)
    )
    return result.scalars().all()


# ── Importar bases de datos ──────────────────────────────────────────────────

class ImportDBOut(BaseModel):
    document_id: uuid.UUID
    file_name: str
    rows_detected: int
    columns: list[str]
    category: str
    task_id: uuid.UUID | None
    message: str


def _parse_tabular_file(file_path: str, file_name: str) -> tuple[list[str], list[dict], str]:
    """
    Parsea un archivo tabular y devuelve (columnas, filas_como_dicts, formato).
    Soporta: .csv, .xlsx, .xls, .json, .ods
    """
    import json as json_mod

    ext = os.path.splitext(file_name)[1].lower()

    if ext == ".csv":
        import csv
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(f, dialect=dialect)
            columns = reader.fieldnames or []
            rows = [row for row in reader]
        return columns, rows, "csv"

    elif ext in (".xlsx", ".xls", ".ods"):
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active
        rows_raw = list(ws.iter_rows(values_only=True))
        wb.close()
        if not rows_raw:
            return [], [], "excel"
        columns = [str(c) if c else f"col_{i}" for i, c in enumerate(rows_raw[0])]
        rows = [
            {columns[j]: cell for j, cell in enumerate(row) if j < len(columns)}
            for row in rows_raw[1:]
        ]
        return columns, rows, "excel"

    elif ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json_mod.load(f)
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            columns = list(data[0].keys())
            return columns, data, "json"
        elif isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    columns = list(val[0].keys())
                    return columns, val, "json"
            columns = list(data.keys())
            return columns, [data], "json"
        return [], [], "json"

    else:
        return [], [], "unknown"


@router.post("/import-db", response_model=list[ImportDBOut])
async def import_database(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Importa archivos de base de datos (.csv, .xlsx, .json).
    Parsea las filas, guarda el archivo como documento, y lanza la IA
    para que clasifique y disemine los datos en las entidades correctas.
    """
    import json as json_mod

    results = []
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    for file in files:
        if not file.filename:
            continue

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in (".csv", ".xlsx", ".xls", ".json", ".ods"):
            results.append(ImportDBOut(
                document_id=uuid.uuid4(),
                file_name=file.filename,
                rows_detected=0,
                columns=[],
                category="otros",
                task_id=None,
                message=f"Formato '{ext}' no soportado. Usa CSV, XLSX, JSON u ODS.",
            ))
            continue

        contents = await file.read()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        with open(file_path, "wb") as f:
            f.write(contents)

        try:
            columns, rows, fmt = _parse_tabular_file(file_path, file.filename)
        except Exception:
            columns, rows, fmt = [], [], "error"

        # Auto-clasificar por contenido de columnas
        cols_lower = " ".join(c.lower() for c in columns)
        if any(k in cols_lower for k in ("factura", "invoice", "importe", "iva", "nif_cliente")):
            auto_cat = "facturas"
        elif any(k in cols_lower for k in ("nomina", "salario", "sueldo", "empleado", "payroll")):
            auto_cat = "nominas"
        elif any(k in cols_lower for k in ("correo", "email", "asunto", "subject", "inbox", "bandeja")):
            auto_cat = "correos"
        elif any(k in cols_lower for k in ("cliente", "customer", "telefono", "empresa", "lead", "contacto")):
            auto_cat = "crm"
        elif any(k in cols_lower for k in ("banco", "iban", "movimiento", "saldo", "transferencia")):
            auto_cat = "bancos"
        elif any(k in cols_lower for k in ("producto", "articulo", "precio", "stock", "referencia")):
            auto_cat = "crm"
        elif any(k in cols_lower for k in ("contrato", "alta", "baja", "puesto", "departamento")):
            auto_cat = "rrhh"
        elif any(k in cols_lower for k in ("impuesto", "modelo", "trimestre", "declaracion")):
            auto_cat = "fiscal"
        else:
            auto_cat = "excels"

        doc = TenantDocument(
            tenant_id=current_user.tenant_id,
            uploaded_by=current_user.id,
            file_name=file.filename,
            file_type=file.content_type or "application/octet-stream",
            file_path=file_path,
            file_size=len(contents),
            category=auto_cat,
            status="uploaded",
            parsed_content=json_mod.dumps({
                "format": fmt,
                "columns": columns,
                "row_count": len(rows),
                "sample_rows": rows[:5],
            }, ensure_ascii=False, default=str),
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        task_id = None
        try:
            from app.services.task_dispatch import dispatch_orchestrator

            intent_summary = (
                f"Importar base de datos '{file.filename}' ({len(rows)} filas, "
                f"columnas: {', '.join(columns[:10])}). "
                f"Clasificar y crear los registros correspondientes en el sistema "
                f"(clientes, facturas, empleados, productos, etc. según el contenido)."
            )
            task = Task(
                tenant_id=current_user.tenant_id,
                created_by=current_user.id,
                domain="excel",
                user_intent=intent_summary,
                status="pending",
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)

            doc.task_id = task.id
            doc.status = "processing"
            await db.commit()
            await db.refresh(doc)

            task_id = task.id
            await dispatch_orchestrator(str(task.id))
        except Exception as e:
            logger.warning("Orchestrator dispatch falló en import para doc %s: %s", doc.id, e)

        results.append(ImportDBOut(
            document_id=doc.id,
            file_name=file.filename,
            rows_detected=len(rows),
            columns=columns[:20],
            category=auto_cat,
            task_id=task_id,
            message=f"{len(rows)} filas detectadas → carpeta '{auto_cat}'. La IA está procesando los datos.",
        ))

    return results
