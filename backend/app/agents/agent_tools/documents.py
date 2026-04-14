"""
Herramientas compartidas para que los agentes IA lean y modifiquen
documentos del Escanear (TenantDocument) en la BD local.
"""

import logging
import os
from datetime import datetime
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import TenantDocument

_logger = logging.getLogger(__name__)


@tool
async def create_document(
    tenant_id: str, file_name: str, content: str, category: str = "informes"
) -> str:
    """
    Crea un nuevo documento de texto (.txt, .csv, .md) en el Gestor Documental (Escanear).
    Util para que el agente genere informes, exporte datos, o guarde resúmenes.
    Args:
        tenant_id: ID del tenant
        file_name: Nombre del archivo, con su extension (ej: informe_ventas.csv, resumen.txt)
        content: Todo el contenido de texto literal a guardar
        category: Categoria donde clasificarlo (ej: 'CRM', 'RRHH', 'informes')
    """
    if not content or not content.strip():
        return "Error: No se puede crear un documento vacío. Genera el contenido antes de llamar a esta herramienta."
    try:
        async with AsyncSessionLocal() as db:
            upload_dir = os.environ.get("UPLOAD_DIR", "/app/uploads")
            if not os.path.exists(upload_dir) and os.name == "nt":
                upload_dir = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")
                )
            os.makedirs(upload_dir, exist_ok=True)

            file_path = os.path.join(upload_dir, file_name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            doc = TenantDocument(
                tenant_id=UUID(tenant_id),
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
async def list_tenant_documents(tenant_id: str, category: str = "all") -> str:
    """
    Lista los documentos del tenant en el Escanear, opcionalmente filtrados por categoria.
    Util antes de modificar un documento — devuelve el ID que necesitas para actualizar.
    Args:
        tenant_id: ID del tenant
        category: Categoria a filtrar ('all', 'RRHH', 'CRM', 'Facturas', 'Nominas', etc.)
    """
    try:
        async with AsyncSessionLocal() as db:
            q = select(TenantDocument).where(TenantDocument.tenant_id == UUID(tenant_id))
            if category != "all":
                q = q.where(TenantDocument.category == category)
            q = q.order_by(TenantDocument.created_at.desc()).limit(15)
            result = await db.execute(q)
            docs = result.scalars().all()

            if not docs:
                return f"No hay documentos{' en la categoria ' + category if category != 'all' else ''} en el escaner."

            lines = []
            for doc in docs:
                lines.append(
                    f"- [{doc.category or 'Sin categoria'}] {doc.file_name} | "
                    f"ID: {doc.id} | "
                    f"Fecha: {doc.created_at.strftime('%d/%m/%Y') if doc.created_at else 'N/A'} | "
                    f"Tipo: {doc.file_type or 'desconocido'}"
                )
            return f"Documentos en el Escanear ({len(docs)}):\n" + "\n".join(lines)
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
                            f"\n\n--- Actualizacion {datetime.now().strftime('%d/%m/%Y %H:%M')} (Agente IA) ---\n"
                        )
                    f.write(new_content)
                doc.file_size = os.path.getsize(doc.file_path)
            else:
                upload_dir = "/app/uploads"
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, doc.file_name or f"doc_{document_id}.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                doc.file_path = file_path
                doc.file_size = len(new_content.encode())

            if append:
                doc.parsed_content = (doc.parsed_content or "") + "\n" + new_content
            else:
                doc.parsed_content = new_content

            doc.processed_at = datetime.now()
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

            if doc.file_path and os.path.exists(doc.file_path):
                try:
                    with open(doc.file_path, encoding="utf-8") as f:
                        content = f.read()
                    return f"Contenido de '{doc.file_name}':\n\n{content[:3000]}{'...(truncado)' if len(content) > 3000 else ''}"
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
