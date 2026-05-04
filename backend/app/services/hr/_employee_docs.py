"""Employee document management â€” upload, list, get, delete, read."""

import os
import uuid as uuid_mod
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import TenantDocument

# â”€â”€ Employee documents â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def list_employee_documents(employee_id: UUID, tenant_id, db: AsyncSession) -> list[dict]:
    category = f"empleado_{employee_id}"
    result = await db.execute(
        select(TenantDocument)
        .where(TenantDocument.tenant_id == tenant_id, TenantDocument.category == category)
        .order_by(desc(TenantDocument.created_at))
    )
    return [
        {
            "id": str(d.id),
            "file_name": d.file_name,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in result.scalars().all()
    ]


async def upload_employee_document(
    employee_id: UUID,
    filename: str,
    content: bytes,
    content_type: str | None,
    tenant_id,
    user_id,
    db: AsyncSession,
) -> dict:
    """Sube documento de empleado. Lanza ValueError si el empleado no existe."""
    from app.services.hr.service import UPLOAD_DIR, get_employee

    emp = await get_employee(employee_id, tenant_id, db)
    if not emp:
        raise ValueError("Empleado no encontrado")

    folder = os.path.join(UPLOAD_DIR, "empleados", str(employee_id))
    os.makedirs(folder, exist_ok=True)
    safe_name = f"{uuid_mod.uuid4().hex[:8]}_{filename}"
    file_path = os.path.join(folder, safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    doc = TenantDocument(
        id=uuid_mod.uuid4(),
        tenant_id=tenant_id,
        uploaded_by=user_id,
        file_name=filename,
        file_type=content_type,
        file_path=file_path,
        file_size=len(content),
        category=f"empleado_{employee_id}",
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {
        "id": str(doc.id),
        "file_name": doc.file_name,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


async def get_employee_document(
    employee_id: UUID,
    doc_id: UUID,
    tenant_id,
    db: AsyncSession,
) -> TenantDocument | None:
    result = await db.execute(
        select(TenantDocument).where(
            TenantDocument.id == doc_id,
            TenantDocument.tenant_id == tenant_id,
            TenantDocument.category == f"empleado_{employee_id}",
        )
    )
    return result.scalar_one_or_none()


async def delete_employee_document(
    employee_id: UUID,
    doc_id: UUID,
    tenant_id,
    db: AsyncSession,
) -> bool:
    doc = await get_employee_document(employee_id, doc_id, tenant_id, db)
    if not doc:
        return False
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.delete(doc)
    await db.commit()
    return True


def read_document_file(doc: TenantDocument) -> tuple[bytes, str, str]:
    """Lee archivo de documento del disco. Lanza FileNotFoundError si no existe."""
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise FileNotFoundError("Documento no encontrado en disco")
    with open(doc.file_path, "rb") as f:
        content = f.read()
    media_type = doc.file_type or "application/octet-stream"
    filename = doc.file_name or "documento"
    return content, media_type, filename
