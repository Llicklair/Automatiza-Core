"""Servicio de dominio para gestión documental.

Encapsula: subida/descarga de archivos, clasificación automática,
escaneo, procesamiento ZIP, importación de BD tabulares, y plantillas de contrato.
"""

import io
import logging
import mimetypes
import os
import uuid
import zipfile
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Task, Tenant, TenantDocument

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")
)

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".odt", ".txt", ".md",
    ".xlsx", ".xls", ".csv", ".ods", ".json",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif",
    ".eml", ".msg", ".zip",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# ── Clasificación automática ─────────────────────────────────────────────────

_EXT_CATEGORY_MAP: dict[str, str] = {
    ".xlsx": "excels", ".xls": "excels", ".csv": "excels", ".ods": "excels",
    ".pdf": "facturas", ".docx": "otros", ".doc": "otros", ".odt": "otros",
    ".png": "otros", ".jpg": "otros", ".jpeg": "otros", ".webp": "otros",
    ".gif": "otros", ".bmp": "otros", ".tiff": "otros", ".tif": "otros",
    ".txt": "otros", ".md": "otros", ".eml": "correos", ".msg": "correos",
}

_MIME_CATEGORY_MAP: dict[str, str] = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excels",
    "application/vnd.ms-excel": "excels",
    "text/csv": "excels",
    "application/pdf": "facturas",
    "message/rfc822": "correos",
    "application/vnd.ms-outlook": "correos",
}


def auto_classify_category(filename: str, content_type: str | None) -> str:
    """Clasifica la categoría inicial de un archivo por extensión y MIME."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in _EXT_CATEGORY_MAP:
        return _EXT_CATEGORY_MAP[ext]
    if content_type and content_type in _MIME_CATEGORY_MAP:
        return _MIME_CATEGORY_MAP[content_type]
    if content_type and content_type.startswith("image/"):
        return "otros"
    return "otros"


# ── Upload y persistencia ────────────────────────────────────────────────────


def validate_upload(filename: str, size: int) -> str:
    """Valida extensión y tamaño. Retorna la extensión. Lanza ValueError si falla."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extensión '{ext}' no permitida")
    if size > MAX_FILE_SIZE:
        raise ValueError("Archivo demasiado grande (máx. 50MB)")
    return ext


def save_file_to_disk(contents: bytes, ext: str) -> str:
    """Guarda bytes en disco con nombre único. Retorna la ruta absoluta."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(contents)
    return file_path


async def _dispatch_task(
    tenant_id, user_id, domain: str, intent: str, doc: TenantDocument, db: AsyncSession,
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
        tenant_id, user_id, "documents",
        f"Procesar documento adjunto: {filename}", doc, db,
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
        tenant_id, user_id, "documents",
        f"Escanear y clasificar documento: {filename}", doc, db,
    )
    return doc, auto_cat


def extract_zip_entries(contents: bytes) -> list[tuple[str, bytes, str | None]]:
    """Extrae archivos de un ZIP. Retorna lista de (filename, data, mime_type).

    Raises zipfile.BadZipFile si el ZIP es inválido.
    """
    entries = []
    with zipfile.ZipFile(io.BytesIO(contents)) as z:
        for info in z.infolist():
            if info.is_dir() or info.filename.startswith("__MACOSX") or info.filename.startswith("."):
                continue
            original_name = os.path.basename(info.filename)
            if not original_name:
                continue
            extracted_data = z.read(info.filename)
            mime_type, _ = mimetypes.guess_type(original_name)
            entries.append((original_name, extracted_data, mime_type))
    return entries


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
            tenant_id, user_id, "documents",
            f"Procesar documento masivo: {original_name}", doc, db,
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
    tenant_id, db: AsyncSession, category: str | None = None,
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
    doc: TenantDocument, file_path: str, tenant_id, db: AsyncSession,
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
            "email": "", "address": "",
        },
        "company": {
            "name": company_name, "nif": company_nif,
            "address": company_address, "phone": "", "email": company_email,
        },
        "lines": [{
            "description": extracted_data.get("concept") or "Servicio",
            "quantity": 1.0, "unit_price": base,
            "tax_percentage": vat_rate, "total": total,
        }],
    }
    if extracted_data.get("notes"):
        invoice_data["notes"] = extracted_data["notes"]
    if extracted_data.get("payment_terms") or extracted_data.get("payment_method"):
        invoice_data["payment_terms"] = extracted_data.get("payment_terms") or extracted_data.get("payment_method")

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
    doc: TenantDocument, new_content: str, append: bool, db: AsyncSession,
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
                f.write(f"\n\n--- Modificacion {datetime.now(UTC).strftime('%d/%m/%Y %H:%M')} ---\n")
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


# ── Plantillas de contrato ───────────────────────────────────────────────────


async def upload_contract_template(
    filename: str, contents: bytes, content_type: str | None,
    tenant_id, user_id, db: AsyncSession,
) -> TenantDocument:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".docx", ".doc", ".odt"}:
        raise ValueError("Solo se permiten archivos .docx, .doc u .odt")
    if len(contents) > 20 * 1024 * 1024:
        raise ValueError("Archivo demasiado grande (máx. 20MB)")

    file_path = save_file_to_disk(contents, ext)
    doc = TenantDocument(
        tenant_id=tenant_id,
        uploaded_by=user_id,
        file_name=filename,
        file_type=content_type,
        file_path=file_path,
        file_size=len(contents),
        category="contract_template",
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def list_contract_templates(tenant_id, db: AsyncSession) -> list[TenantDocument]:
    result = await db.execute(
        select(TenantDocument)
        .where(
            TenantDocument.tenant_id == tenant_id,
            TenantDocument.category == "contract_template",
        )
        .order_by(desc(TenantDocument.created_at))
        .limit(50)
    )
    return list(result.scalars().all())


async def get_contract_template(
    doc_id: uuid.UUID, tenant_id, db: AsyncSession,
) -> TenantDocument | None:
    result = await db.execute(
        select(TenantDocument).where(
            TenantDocument.id == doc_id,
            TenantDocument.tenant_id == tenant_id,
            TenantDocument.category == "contract_template",
        )
    )
    return result.scalar_one_or_none()


async def delete_contract_template(doc_id: uuid.UUID, tenant_id, db: AsyncSession) -> bool:
    doc = await get_contract_template(doc_id, tenant_id, db)
    if not doc:
        return False
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            logger.warning("No se pudo eliminar archivo: %s", doc.file_path)
    await db.delete(doc)
    await db.commit()
    return True


def validate_template_on_disk(doc: TenantDocument) -> str:
    """Validates a contract template file exists on disk. Returns the file path.

    Raises FileNotFoundError if the file is not available.
    """
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise FileNotFoundError("Archivo de plantilla no disponible en disco")
    return doc.file_path


def preview_contract_html(file_path: str) -> dict:
    """Vista previa HTML de un .docx. Lanza ImportError, FileNotFoundError, ValueError."""
    from app.services.documents.docx_preview import docx_to_preview_html
    return docx_to_preview_html(file_path)


def save_contract_html(html: str, file_path: str) -> int:
    """Guarda HTML editado como .docx. Retorna nuevo tamaño. Lanza ImportError, ValueError, OSError."""
    from app.services.documents.docx_html_save import save_html_as_docx
    save_html_as_docx(html, file_path)
    return os.path.getsize(file_path)


async def save_contract_html_and_update(
    html: str, doc: TenantDocument, db: AsyncSession,
) -> int:
    """Guarda HTML como .docx y actualiza el tamaño en BD. Retorna nuevo tamaño.

    Lanza FileNotFoundError, ImportError, ValueError, OSError.
    """
    file_path = validate_template_on_disk(doc)
    new_size = save_contract_html(html, file_path)
    doc.file_size = new_size
    await db.commit()
    await db.refresh(doc)
    return new_size


async def generate_contract_from_template(
    tpl_doc: TenantDocument, entity_type: str, entity_id: uuid.UUID,
    tenant_id, db: AsyncSession,
) -> tuple[bytes, str]:
    """Genera contrato rellenando plantilla. Retorna (docx_bytes, filename).

    Lanza ValueError, ImportError, HTTPException-equivalents via ValueError.
    """
    from sqlalchemy import select as sa_select

    from app.db.models.auth import Tenant
    from app.services.crm.contract_generator import (
        build_context_for_client,
        build_context_for_employee,
        generate_contract,
    )

    tenant_result = await db.execute(sa_select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()

    if entity_type == "client":
        from app.db.models.crm import Client
        r = await db.execute(
            sa_select(Client).where(Client.id == entity_id, Client.tenant_id == tenant_id)
        )
        entity = r.scalar_one_or_none()
        if not entity:
            raise ValueError("Cliente no encontrado")
        context = build_context_for_client(entity, tenant)
    elif entity_type == "employee":
        from app.db.models.hr import Employee
        r = await db.execute(
            sa_select(Employee).where(Employee.id == entity_id, Employee.tenant_id == tenant_id)
        )
        entity = r.scalar_one_or_none()
        if not entity:
            raise ValueError("Empleado no encontrado")
        context = build_context_for_employee(entity, tenant)
    else:
        raise ValueError("entity_type debe ser 'client' o 'employee'")

    docx_bytes = generate_contract(tpl_doc.file_path, context)
    base_name = os.path.splitext(tpl_doc.file_name)[0]
    entity_slug = (entity.name or "contrato").replace(" ", "_")
    filename = f"{base_name}_{entity_slug}_BORRADOR.docx"

    return docx_bytes, filename


# ── Importación de BD tabular ────────────────────────────────────────────────


def parse_tabular_file(file_path: str, file_name: str) -> tuple[list[str], list[dict], str]:
    """Parsea archivo tabular. Retorna (columnas, filas, formato). Soporta csv/xlsx/xls/json/ods."""
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

    return [], [], "unknown"


def auto_classify_tabular(columns: list[str]) -> str:
    """Clasifica categoría de un archivo tabular por nombres de columnas."""
    cols_lower = " ".join(c.lower() for c in columns)
    if any(k in cols_lower for k in ("factura", "invoice", "importe", "iva", "nif_cliente")):
        return "facturas"
    if any(k in cols_lower for k in ("nomina", "salario", "sueldo", "empleado", "payroll")):
        return "nominas"
    if any(k in cols_lower for k in ("correo", "email", "asunto", "subject", "inbox", "bandeja")):
        return "correos"
    if any(k in cols_lower for k in ("cliente", "customer", "telefono", "empresa", "lead", "contacto")):
        return "crm"
    if any(k in cols_lower for k in ("banco", "iban", "movimiento", "saldo", "transferencia")):
        return "bancos"
    if any(k in cols_lower for k in ("producto", "articulo", "precio", "stock", "referencia")):
        return "crm"
    if any(k in cols_lower for k in ("contrato", "alta", "baja", "puesto", "departamento")):
        return "rrhh"
    if any(k in cols_lower for k in ("impuesto", "modelo", "trimestre", "declaracion")):
        return "fiscal"
    return "excels"


async def import_tabular_file(
    filename: str, contents: bytes, content_type: str | None,
    tenant_id, user_id, db: AsyncSession,
) -> tuple[TenantDocument, list[str], int, str, uuid.UUID | None]:
    """Importa un archivo tabular. Retorna (doc, columns, row_count, auto_cat, task_id)."""
    import json as json_mod

    ext = os.path.splitext(filename)[1].lower()
    file_path = save_file_to_disk(contents, ext)

    try:
        columns, rows, fmt = parse_tabular_file(file_path, filename)
    except Exception:
        columns, rows, fmt = [], [], "error"

    auto_cat = auto_classify_tabular(columns)

    doc = TenantDocument(
        tenant_id=tenant_id,
        uploaded_by=user_id,
        file_name=filename,
        file_type=content_type or "application/octet-stream",
        file_path=file_path,
        file_size=len(contents),
        category=auto_cat,
        status="uploaded",
        parsed_content=json_mod.dumps(
            {"format": fmt, "columns": columns, "row_count": len(rows), "sample_rows": rows[:5]},
            ensure_ascii=False, default=str,
        ),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    task_id = None
    try:
        from app.services.workflow.task_dispatch import dispatch_orchestrator

        intent_summary = (
            f"Importar base de datos '{filename}' ({len(rows)} filas, "
            f"columnas: {', '.join(columns[:10])}). "
            f"Clasificar y crear los registros correspondientes en el sistema "
            f"(clientes, facturas, empleados, productos, etc. según el contenido)."
        )
        task = Task(
            tenant_id=tenant_id, created_by=user_id,
            domain="excel", user_intent=intent_summary, status="pending",
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

    return doc, columns[:20], len(rows), auto_cat, task_id
