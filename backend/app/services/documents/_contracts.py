"""Gestión de plantillas de contrato: CRUD, preview, guardado y generación."""

import logging
import os
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import TenantDocument
from app.services.documents._file_ops import save_file_to_disk

logger = logging.getLogger(__name__)


async def upload_contract_template(
    filename: str,
    contents: bytes,
    content_type: str | None,
    tenant_id,
    user_id,
    db: AsyncSession,
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
    doc_id: uuid.UUID,
    tenant_id,
    db: AsyncSession,
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
    html: str,
    doc: TenantDocument,
    db: AsyncSession,
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
    tpl_doc: TenantDocument,
    entity_type: str,
    entity_id: uuid.UUID,
    tenant_id,
    db: AsyncSession,
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
