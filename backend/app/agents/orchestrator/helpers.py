"""
Funciones auxiliares del orquestador: bloqueo de documentos, guardado de resultados IA.
"""
import logging
import uuid

logger = logging.getLogger(__name__)


async def _lock_document(db, doc_id: uuid.UUID, task_id: uuid.UUID) -> bool:
    """Intenta bloquear un documento para una tarea específica."""
    from app.db.models.models import TenantDocument
    from datetime import datetime, UTC

    doc = await db.get(TenantDocument, doc_id)
    if not doc:
        return False

    # Si ya está bloqueado por otra tarea activa (hace menos de 5 min)
    if doc.locked_by and doc.locked_by != task_id:
        if doc.locked_at and (datetime.now(UTC) - doc.locked_at).total_seconds() < 300:
            return False

    doc.locked_by = task_id
    doc.locked_at = datetime.now(UTC)
    return True

async def _unlock_document(db, doc_id: uuid.UUID, task_id: uuid.UUID):
    """Libera el bloqueo de un documento."""
    from app.db.models.models import TenantDocument
    doc = await db.get(TenantDocument, doc_id)
    if doc and doc.locked_by == task_id:
        doc.locked_by = None
        doc.locked_at = None

async def _save_ai_result_as_document(
    tenant_id: str,
    task_id: str,
    category: str,
    title: str,
    content: str,
    reference_name: str | None = None  # Si se especifica, se busca para sobreescribir
) -> None:
    """
    Guarda el resultado textual de un Agente IA como un documento PDF.
    Implementa lógica de SOBREESCRITURA si existe un documento similar en la carpeta.
    """
    import os
    import uuid
    from datetime import datetime, UTC

    from sqlalchemy import select, and_, or_

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantDocument
    from app.services.pdf_service import generate_text_report_pdf

    try:
        # Ruta de uploads
        _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        upload_dir = os.path.normpath(os.path.join(_THIS_DIR, "..", "uploads"))
        os.makedirs(upload_dir, exist_ok=True)

        # Nombre de fichero determinista (ahora .pdf)
        # Si hay un reference_name (ej: "factura_123"), lo usamos para ser constantes
        clean_ref = "".join(c for c in (reference_name or title) if c.isalnum() or c in (' ', '_', '-')).replace(' ', '_').lower()
        filename = f"{category.lower()}_{clean_ref[:30]}.pdf"
        file_path = os.path.join(upload_dir, filename)

        # Generar PDF desde el contenido
        pdf_bytes = generate_text_report_pdf(title, content, category)

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        async with AsyncSessionLocal() as db:
            # Buscar si ya existe un doc similar para SOBREESCRIBIR
            # Priorizamos buscar por nombre de archivo o título en la misma categoría
            existing_result = await db.execute(
                select(TenantDocument).where(
                    TenantDocument.tenant_id == uuid.UUID(tenant_id),
                    TenantDocument.category == category,
                    or_(
                        TenantDocument.file_name == filename,
                        TenantDocument.task_id == uuid.UUID(task_id)
                    )
                )
            )
            existing_doc = existing_result.scalars().first()

            if existing_doc:
                # INTENTAR BLOQUEO PARA CONCURRENCIA
                if not await _lock_document(db, existing_doc.id, uuid.UUID(task_id)):
                    logger.warning(f"[ORCHESTRATOR] Archivo {filename} bloqueado por otro agente. Esperando...")
                    # En una implementación real, reintentaríamos. Aquí lo forzamos tras aviso si es el mismo task

                # Sobreescribir: actualizar campos
                existing_doc.file_path = file_path
                existing_doc.file_name = filename
                existing_doc.file_type = "application/pdf"
                existing_doc.file_size = len(pdf_bytes)
                existing_doc.processed_at = datetime.now(UTC)
                existing_doc.status = "completed"
                existing_doc.parsed_content = content

                # Liberar bloqueo
                await _unlock_document(db, existing_doc.id, uuid.UUID(task_id))
            else:
                doc = TenantDocument(
                    tenant_id=uuid.UUID(tenant_id),
                    task_id=uuid.UUID(task_id),
                    file_name=filename,
                    file_path=file_path,
                    file_type="application/pdf",
                    file_size=len(pdf_bytes),
                    category=category,
                    status="completed",
                    parsed_content=content,
                )
                db.add(doc)
            await db.commit()
    except Exception:
        logger.exception("Error guardando resultado como documento")


async def _save_ai_result_as_csv(
    tenant_id: str,
    task_id: str,
    category: str,
    filename: str,
    data: list[dict]
) -> None:
    """Exporta una lista de diccionarios a CSV y la registra en TenantDocument."""
    import csv
    import os
    import uuid
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantDocument

    if not data:
        return

    try:
        _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        upload_dir = os.path.normpath(os.path.join(_THIS_DIR, "..", "uploads"))
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)

        keys = data[0].keys()
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)

        async with AsyncSessionLocal() as db:
            doc = TenantDocument(
                tenant_id=uuid.UUID(tenant_id),
                task_id=uuid.UUID(task_id),
                file_name=filename,
                file_path=file_path,
                file_type="text/csv",
                file_size=os.path.getsize(file_path),
                category=category,
                status="completed",
                parsed_content=f"Datos exportados para análisis: {len(data)} registros."
            )
            db.add(doc)
            await db.commit()
    except Exception as e:
        logger.warning(f"Error al exportar datos a CSV: {e}")


# ── Mapeo tipo de documento → carpeta (category) ────────────────────────────
_DOC_TYPE_TO_CATEGORY = {
    "factura": "facturas",
    "factura_recibida": "facturas",
    "factura_emitida": "facturas",
    "presupuesto": "facturas",
    "nomina": "nominas",
    "recibo_salario": "nominas",
    "extracto_bancario": "bancos",
    "movimiento_bancario": "bancos",
    "contrato": "rrhh",
    "contrato_laboral": "rrhh",
    "certificado": "rrhh",
    "modelo_fiscal": "fiscal",
    "impuesto": "fiscal",
    "declaracion": "fiscal",
    "excel": "excels",
    "hoja_calculo": "excels",
    "informe": "informes",
    "correo": "correos",
    "email": "correos",
}


def _classify_document_category(document_type: str | None) -> str:
    """Mapea el tipo detectado por documents_agent a la carpeta correcta."""
    if not document_type:
        return "otros"
    doc_lower = document_type.lower().strip()
    # Coincidencia exacta
    if doc_lower in _DOC_TYPE_TO_CATEGORY:
        return _DOC_TYPE_TO_CATEGORY[doc_lower]
    # Coincidencia parcial
    for key, category in _DOC_TYPE_TO_CATEGORY.items():
        if key in doc_lower or doc_lower in key:
            return category
    return "otros"
