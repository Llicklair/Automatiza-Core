"""Servicio de dominio para gestión documental.

Encapsula: subida/descarga de archivos, clasificación automática,
escaneo, procesamiento ZIP, importación de BD tabulares, y plantillas de contrato.

Sub-módulos extraídos:
- _file_ops: validación, guardado, clasificación por extensión, ZIP
- _contracts: plantillas de contrato (CRUD, preview, generación)
- _tabular: parseo e importación de archivos tabulares
"""

import io
import logging
import os
import uuid
import zipfile
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Task, Tenant, TenantDocument

# ── Re-exports desde sub-módulos ─────────────────────────────────────────────
from app.services.documents._file_ops import (
    UPLOAD_DIR,
    auto_classify_category,
    extract_zip_entries,
    save_file_to_disk,
    validate_upload,
)

logger = logging.getLogger(__name__)


# ── Dispatch interno ────────────────────────────────────────────────────────


async def _dispatch_task(
    tenant_id,
    user_id,
    domain: str,
    intent: str,
    doc: TenantDocument,
    db: AsyncSession,
) -> None:
    """Crea Task + lanza orchestrator. No falla si el dispatch falla."""
    try:
        from app.services.workflow.task_dispatch import dispatch_orchestrator

        task = Task(
            tenant_id=tenant_id,
            created_by=user_id,
            domain=domain,
            user_intent=intent,
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


# ── Upload ──────────────────────────────────────────────────────────────────


async def upload_single(
    filename: str,
    contents: bytes,
    content_type: str | None,
    tenant_id,
    user_id,
    db: AsyncSession,
    category: str | None = None,
) -> TenantDocument:
    """Sube un archivo, lo persiste y lanza procesamiento IA."""
    ext = validate_upload(filename, len(contents))
    file_path = save_file_to_disk(contents, ext)

    doc = TenantDocument(
        tenant_id=tenant_id,
        uploaded_by=user_id,
        file_name=filename,
        file_type=content_type,
        file_path=file_path,
        file_size=len(contents),
        category=category,
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    await _dispatch_task(
        tenant_id,
        user_id,
        "documents",
        f"Procesar documento adjunto: {filename}",
        doc,
        db,
    )
    return doc


# ── Scan (clasificación automática) ──────────────────────────────────────────


async def scan_single(
    filename: str,
    contents: bytes,
    content_type: str | None,
    tenant_id,
    user_id,
    db: AsyncSession,
) -> tuple[TenantDocument, str]:
    """Procesa un archivo para scan: guardar, clasificar, lanzar IA. Retorna (doc, auto_category)."""
    ext = os.path.splitext(filename)[1]
    file_path = save_file_to_disk(contents, ext)
    auto_cat = auto_classify_category(filename, content_type)

    doc = TenantDocument(
        tenant_id=tenant_id,
        uploaded_by=user_id,
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

    await _dispatch_task(
        tenant_id,
        user_id,
        "documents",
        f"Escanear y clasificar documento: {filename}",
        doc,
        db,
    )
    return doc, auto_cat


# ── Bulk upload (ZIP) ────────────────────────────────────────────────────────


async def upload_bulk(
    contents: bytes,
    tenant_id,
    user_id,
    db: AsyncSession,
    category: str | None = None,
) -> list[TenantDocument]:
    """Extrae archivos de un ZIP y los procesa individualmente."""
    entries = extract_zip_entries(contents)
    docs = []
    for original_name, extracted_data, mime_type in entries:
        ext = os.path.splitext(original_name)[1]
        file_path = save_file_to_disk(extracted_data, ext)

        doc = TenantDocument(
            tenant_id=tenant_id,
            uploaded_by=user_id,
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

        await _dispatch_task(
            tenant_id,
            user_id,
            "documents",
            f"Procesar documento masivo: {original_name}",
            doc,
            db,
        )
        docs.append(doc)
    return docs


# ── Export ────────────────────────────────────────────────────────────────────


async def export_all(tenant_id, db: AsyncSession) -> bytes:
    """Exporta todos los documentos del tenant como ZIP en memoria."""
    result = await db.execute(
        select(TenantDocument)
        .where(TenantDocument.tenant_id == tenant_id)
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
            base_name = doc.file_name or os.path.basename(normalized)
            base, ext = os.path.splitext(base_name)
            unique_name = base_name
            counter = 1
            while unique_name in added_names:
                unique_name = f"{base}_{counter}{ext}"
                counter += 1
            added_names.add(unique_name)
            zf.write(normalized, unique_name)

    return zip_buffer.getvalue()


# ── List / Get / Delete ──────────────────────────────────────────────────────


async def list_documents(
    tenant_id,
    db: AsyncSession,
    category: str | None = None,
) -> list[TenantDocument]:
    query = (
        select(TenantDocument)
        .where(TenantDocument.tenant_id == tenant_id)
        .order_by(desc(TenantDocument.created_at))
        .limit(50)
    )
    if category and category != "all":
        query = query.where(TenantDocument.category == category)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_document(doc_id: uuid.UUID, tenant_id, db: AsyncSession) -> TenantDocument | None:
    result = await db.execute(
        select(TenantDocument).where(
            TenantDocument.id == doc_id,
            TenantDocument.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_document(doc_id: uuid.UUID, tenant_id, db: AsyncSession) -> bool:
    """Elimina documento de BD y disco. Retorna False si no existe."""
    doc = await get_document(doc_id, tenant_id, db)
    if not doc:
        return False

    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            logger.warning("No se pudo eliminar archivo: %s", doc.file_path)
    elif doc.file_name:
        fallback = os.path.join(UPLOAD_DIR, doc.file_name)
        if os.path.exists(fallback):
            try:
                os.remove(fallback)
            except OSError:
                logger.warning("No se pudo eliminar archivo: %s", fallback)

    await db.delete(doc)
    await db.commit()
    return True


# ── Download con regeneración PDF ────────────────────────────────────────────


def _resolve_file_path(doc: TenantDocument) -> str | None:
    """Resuelve la ruta del archivo en disco, con fallback por nombre."""
    if not doc.file_path:
        return None
    file_path = os.path.normpath(doc.file_path)
    if os.path.exists(file_path):
        return file_path
    if doc.file_name:
        fallback = os.path.join(UPLOAD_DIR, doc.file_name)
        if os.path.exists(fallback):
            return fallback
    return None


async def prepare_download(doc: TenantDocument, tenant_id, db: AsyncSession) -> str:
    """Prepara archivo para descarga, regenerando PDF si es necesario.

    Retorna la ruta del archivo. Lanza FileNotFoundError o ValueError si falla.
    """
    file_path = _resolve_file_path(doc)
    if not file_path:
        raise FileNotFoundError(f"Archivo no disponible en disco: {doc.file_path}")

    # Si es un PDF de factura IA antiguo, intentar regenerar
    is_ai_invoice_pdf = (doc.file_name or "").lower().startswith("factura_ia_") and (
        (doc.file_type or "").lower() == "application/pdf"
    )
    if is_ai_invoice_pdf:
        try:
            with open(file_path, "rb") as f:
                header = f.read(5)
            if header != b"%PDF-":
                await _regenerate_ai_invoice_pdf(doc, file_path, tenant_id, db)
        except Exception:
            pass  # No bloquear descarga por errores de regeneración

    return file_path


async def _regenerate_ai_invoice_pdf(
    doc: TenantDocument,
    file_path: str,
    tenant_id,
    db: AsyncSession,
) -> None:
    """Regenera un PDF de factura IA a partir de los datos de la Task asociada."""
    extracted_data = None
    if doc.task_id:
        task_result = await db.execute(
            select(Task).where(Task.id == doc.task_id, Task.tenant_id == tenant_id)
        )
        task = task_result.scalar_one_or_none()
        if task and task.agent_results:
            for r in task.agent_results or []:
                if not isinstance(r, dict):
                    continue
                if r.get("agent") != "billing":
                    continue
                out = r.get("output") or {}
                if isinstance(out, dict) and out.get("extracted_data"):
                    extracted_data = out.get("extracted_data")
                    break

    if not isinstance(extracted_data, dict):
        raise ValueError("No se encontraron datos para regenerar el PDF")

    from app.services.pdf import generate_invoice_pdf

    base = float(extracted_data.get("amount_base") or 0)
    vat_rate = float(extracted_data.get("vat_rate") or 21)
    tax = round(base * vat_rate / 100, 2)
    total = round(base + tax, 2)
    task_id_str = str(doc.task_id) if doc.task_id else ""
    invoice_number = f"IA-{task_id_str[:8].upper()}" if task_id_str else "IA"

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
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
        invoice_data["payment_terms"] = extracted_data.get("payment_terms") or extracted_data.get(
            "payment_method"
        )

    pdf_bytes = generate_invoice_pdf(invoice_data)
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("No se pudo regenerar el PDF (bytes inválidos)")

    with open(file_path, "wb") as f:
        f.write(pdf_bytes)
    doc.file_size = len(pdf_bytes)
    doc.file_type = "application/pdf"
    doc.processed_at = datetime.now(UTC)
    doc.status = "completed"
    await db.commit()


# ── Update content ───────────────────────────────────────────────────────────


async def update_content(
    doc: TenantDocument,
    new_content: str,
    append: bool,
    db: AsyncSession,
) -> TenantDocument:
    """Actualiza el contenido textual de un documento. Lanza ValueError si es PDF."""
    if doc.file_type and "pdf" in doc.file_type.lower():
        raise ValueError(
            "No se puede modificar directamente un PDF. Modifica los datos originales y regenera el PDF."
        )

    if doc.file_path and os.path.exists(doc.file_path):
        mode = "a" if append else "w"
        with open(doc.file_path, mode, encoding="utf-8") as f:
            if append:
                f.write(
                    f"\n\n--- Modificacion {datetime.now(UTC).strftime('%d/%m/%Y %H:%M')} ---\n"
                )
            f.write(new_content)
        doc.file_size = os.path.getsize(doc.file_path)
    else:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, doc.file_name or f"doc_{doc.id}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        doc.file_path = file_path
        doc.file_size = len(new_content.encode())

    if append:
        doc.parsed_content = (doc.parsed_content or "") + "\n" + new_content
    else:
        doc.parsed_content = new_content

    doc.processed_at = datetime.now(UTC)
    doc.status = "completed"
    await db.commit()
    await db.refresh(doc)
    return doc
