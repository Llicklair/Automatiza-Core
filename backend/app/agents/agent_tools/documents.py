"""
Herramientas compartidas para que los agentes IA lean y modifiquen
documentos del Escanear (TenantDocument) en la BD local.
"""

import asyncio
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select

from app.agents.agent_tools.reports import _resolve_upload_dir
from app.db.base import AsyncSessionLocal
from app.db.models.models import TenantDocument

_logger = logging.getLogger(__name__)

# Categorías visibles en la UI (frontend/.../documentos/page.tsx FOLDERS).
# Cualquier otra categoría → mapea a "otros" (catch-all del UI).
_VALID_CATEGORIES = {
    "facturas", "bancos", "nominas", "fiscal", "crm", "excels",
    "informes", "correos", "automatizaciones", "rrhh", "otros",
}


def _normalize_category(category: str | None) -> str:
    """Mapea categorías arbitrarias a una de las visibles en la UI."""
    if not category:
        return "otros"
    cat = category.strip().lower()
    return cat if cat in _VALID_CATEGORIES else "otros"


@tool
async def create_document(
    tenant_id: str, file_name: str, content: str, category: str = "otros"
) -> str:
    """
    Crea un nuevo documento de texto (.txt, .csv, .md) en el Gestor Documental (Escanear).
    Util para que el agente genere informes, exporte datos, o guarde resúmenes.
    Args:
        tenant_id: ID del tenant
        file_name: Nombre del archivo, con su extension (ej: informe_ventas.csv, resumen.txt)
        content: Todo el contenido de texto literal a guardar
        category: Categoría visible en la UI. Valores válidos: 'facturas',
            'bancos', 'nominas', 'fiscal', 'crm', 'excels', 'informes',
            'correos', 'automatizaciones', 'rrhh', 'otros'. Cualquier valor
            no listado se guarda como 'otros' (catch-all). Para notas o
            recordatorios usa 'otros'.
    """
    if not content or not content.strip():
        return "Error: No se puede crear un documento vacío. Genera el contenido antes de llamar a esta herramienta."
    try:
        from app.core.tenant_context import get_current_task

        current_task_id = get_current_task()
        async with AsyncSessionLocal() as db:
            category = _normalize_category(category)

            # Guard cross-dispatcher: si esta task ya creó un documento en
            # la misma categoría, no duplicar. Sucede cuando el coordinator
            # descompone p.ej. "informe PDF" en billing+documents y ambos
            # invocan tools de creación. El primero gana, el segundo se
            # convierte en no-op informativo.
            if current_task_id:
                existing = await db.execute(
                    select(TenantDocument.id, TenantDocument.file_name).where(
                        TenantDocument.tenant_id == UUID(tenant_id),
                        TenantDocument.task_id == UUID(current_task_id),
                        TenantDocument.category == category,
                    )
                )
                existing_doc = existing.first()
                if existing_doc:
                    return (
                        f"Ya existe un documento '{existing_doc.file_name}' "
                        f"(ID: {existing_doc.id}) creado para esta tarea en la "
                        f"categoría '{category}'. No se crea uno duplicado. "
                        f"Si quieres añadir contenido al existente, usa "
                        f"update_existing_document con ese document_id."
                    )

            upload_dir = _resolve_upload_dir(category)
            file_path = os.path.join(upload_dir, file_name)
            await asyncio.to_thread(Path(file_path).write_text, content, encoding="utf-8")

            doc = TenantDocument(
                tenant_id=UUID(tenant_id),
                task_id=UUID(current_task_id) if current_task_id else None,
                file_name=file_name,
                file_path=file_path,
                file_type="text/plain",
                file_size=len(content.encode()),
                category=category,
                status="completed",
                parsed_content=content,
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            return f"Documento '{file_name}' creado correctamente. ID: {doc.id} en la categoria '{category}'."
    except Exception as e:
        return f"Error creando el documento: {str(e)}"


@tool
async def list_tenant_documents(
    tenant_id: str, category: str = "all", limit: int = 50, offset: int = 0
) -> str:
    """
    Lista los documentos del tenant en el Gestor Documental, opcionalmente
    filtrados por categoria. Util antes de modificar un documento — devuelve
    el ID que necesitas para actualizar.

    Soporta pagination: cuando hay más documentos que `limit`, el output
    incluye el total y indica cómo pedir la siguiente página con `offset`.

    Args:
        tenant_id: ID del tenant
        category: Categoria a filtrar (valores: 'all', 'facturas', 'bancos',
            'nominas', 'fiscal', 'crm', 'excels', 'informes', 'correos',
            'automatizaciones', 'rrhh', 'otros'). Default 'all'.
        limit: Número máximo de documentos a devolver. Default 50 (max útil 200).
        offset: Saltar los primeros N documentos (para pagination). Default 0.
    """
    try:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        async with AsyncSessionLocal() as db:
            from sqlalchemy import func as _f
            count_q = select(_f.count()).select_from(TenantDocument).where(
                TenantDocument.tenant_id == UUID(tenant_id)
            )
            if category != "all":
                count_q = count_q.where(TenantDocument.category == category)
            total = (await db.execute(count_q)).scalar() or 0

            q = select(TenantDocument).where(TenantDocument.tenant_id == UUID(tenant_id))
            if category != "all":
                q = q.where(TenantDocument.category == category)
            q = q.order_by(TenantDocument.created_at.desc()).limit(limit).offset(offset)
            result = await db.execute(q)
            docs = result.scalars().all()

            if not docs:
                return f"No hay documentos{' en la categoria ' + category if category != 'all' else ''} en el escaner."

            lines = [
                f"- [{doc.category or 'Sin categoria'}] {doc.file_name} | "
                f"ID: {doc.id} | "
                f"Fecha: {doc.created_at.strftime('%d/%m/%Y') if doc.created_at else 'N/A'} | "
                f"Tipo: {doc.file_type or 'desconocido'}"
                for doc in docs
            ]
            header = (
                f"Documentos en el Gestor "
                f"({'categoria ' + category + ', ' if category != 'all' else ''}"
                f"mostrando {len(docs)} de {total} totales"
                f"{', desde offset ' + str(offset) if offset else ''}):"
            )
            footer = ""
            if offset + len(docs) < total:
                next_offset = offset + len(docs)
                footer = (
                    f"\n\n[Hay {total - next_offset} documentos más. Llama de nuevo "
                    f"con offset={next_offset} para verlos.]"
                )
            return header + "\n" + "\n".join(lines) + footer
    except Exception as e:
        return f"Error listando documentos: {str(e)}"


@tool
async def update_existing_document(
    tenant_id: str, document_id: str, new_content: str, append: bool = False
) -> str:
    """
    Modifica el contenido de un documento existente en el Escanear.
    Solo funciona con documentos de texto (TXT). Los PDFs no se pueden editar directamente.
    Args:
        tenant_id: ID del tenant
        document_id: ID del documento a modificar (obtenlo con list_tenant_documents)
        new_content: Nuevo contenido a escribir en el documento
        append: Si True, adjunta el contenido al final. Si False (default), reemplaza todo el contenido.
    """
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
                return f"Error: Documento con ID {document_id} no encontrado en el Escanear."

            if doc.file_type and "pdf" in doc.file_type.lower():
                return (
                    "No puedo modificar directamente un PDF. "
                    "Para facturas, modifica los datos en el ERP y genera un nuevo PDF."
                )

            if doc.file_path and os.path.exists(doc.file_path):
                mode = "a" if append else "w"
                with open(doc.file_path, mode, encoding="utf-8") as f:
                    if append:
                        f.write(
                            f"\n\n--- Actualizacion {datetime.now(UTC).strftime('%d/%m/%Y %H:%M')} (Agente IA) ---\n"
                        )
                    f.write(new_content)
                doc.file_size = os.path.getsize(doc.file_path)
            else:
                upload_dir = _resolve_upload_dir(_normalize_category(doc.category))
                file_path = os.path.join(upload_dir, doc.file_name or f"doc_{document_id}.txt")
                await asyncio.to_thread(Path(file_path).write_text, new_content, encoding="utf-8")
                doc.file_path = file_path
                doc.file_size = len(new_content.encode())

            if append:
                doc.parsed_content = (doc.parsed_content or "") + "\n" + new_content
            else:
                doc.parsed_content = new_content

            doc.processed_at = datetime.now(UTC)
            doc.status = "completed"
            await db.commit()

            action = "adjuntado al" if append else "reemplazado en el"
            return (
                f"Documento '{doc.file_name}' actualizado correctamente. "
                f"Contenido {action} archivo. "
                f"Nuevo tamanyo: {doc.file_size} bytes. "
                f"El cambio ya es visible en el Escanear."
            )
    except Exception as e:
        return f"Error actualizando documento: {str(e)}"


@tool
async def get_document_content(tenant_id: str, document_id: str) -> str:
    """
    Lee el contenido actual de un documento del Escanear.
    Util para ver que hay antes de modificar.
    Args:
        tenant_id: ID del tenant
        document_id: ID del documento
    """
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
                return f"Documento {document_id} no encontrado."

            # Extensiones binarias: leer como utf-8 garantiza UnicodeDecodeError.
            # Saltamos directo a parsed_content (que ya contiene el texto extraído
            # por OCR/parser cuando el documento se subió).
            _BINARY_EXTS = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp",
                            ".xlsx", ".xls", ".docx", ".doc", ".pptx", ".zip")
            _is_binary = doc.file_path and doc.file_path.lower().endswith(_BINARY_EXTS)

            if doc.file_path and os.path.exists(doc.file_path) and not _is_binary:
                try:
                    content = await asyncio.to_thread(
                        Path(doc.file_path).read_text, encoding="utf-8"
                    )
                    return f"Contenido de '{doc.file_name}':\n\n{content[:3000]}{'...(truncado)' if len(content) > 3000 else ''}"
                except UnicodeDecodeError:
                    # Archivo no era texto pese a extensión "segura". Fallback silencioso.
                    _logger.debug(
                        "File %s no es UTF-8 válido, usando parsed_content",
                        doc.file_path,
                    )
                except Exception:
                    _logger.warning(
                        "Failed to read file %s from disk, falling back to DB",
                        doc.file_path,
                        exc_info=True,
                    )

            if doc.parsed_content:
                return f"Contenido de '{doc.file_name}':\n\n{doc.parsed_content[:3000]}"

            return f"El documento '{doc.file_name}' existe pero no tiene contenido legible (puede ser un PDF o imagen)."
    except Exception as e:
        return f"Error leyendo documento: {str(e)}"
