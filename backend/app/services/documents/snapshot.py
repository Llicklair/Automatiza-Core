"""Servicio para generación y gestión de informes snapshot (PDF mensuales)."""

import logging
import os
import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Tenant, TenantDocument
from app.services.documents._file_ops import UPLOAD_DIR

logger = logging.getLogger(__name__)


async def get_tenant_name(tenant_id, db: AsyncSession) -> str:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    return tenant.name if tenant and tenant.name else "Tu empresa"


async def save_snapshot_report(
    pdf_bytes: bytes,
    month: str,
    tenant_id,
    user_id,
    executive_summary: str | None,
    db: AsyncSession,
) -> TenantDocument:
    """Guarda un PDF de snapshot en disco y lo persiste en tenant_documents."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_name = f"informe_{month}_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    with open(file_path, "wb") as fh:
        fh.write(pdf_bytes)

    doc = TenantDocument(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        uploaded_by=user_id,
        file_name=file_name,
        file_type="application/pdf",
        file_path=file_path,
        file_size=len(pdf_bytes),
        status="processed",
        parsed_content=executive_summary,
        category="informes",
        created_at=datetime.now(UTC),
        processed_at=datetime.now(UTC),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def list_snapshot_reports(tenant_id, db: AsyncSession) -> list[TenantDocument]:
    """Lista todos los informes mensuales generados para un tenant."""
    result = await db.execute(
        select(TenantDocument)
        .where(
            and_(
                TenantDocument.tenant_id == tenant_id,
                TenantDocument.category == "informes",
            )
        )
        .order_by(TenantDocument.created_at.desc())
    )
    return list(result.scalars().all())


async def get_snapshot_report(
    report_id: uuid.UUID, tenant_id, db: AsyncSession
) -> TenantDocument | None:
    """Obtiene un informe por ID, verificando pertenencia al tenant."""
    result = await db.execute(
        select(TenantDocument).where(
            and_(
                TenantDocument.id == report_id,
                TenantDocument.tenant_id == tenant_id,
                TenantDocument.category == "informes",
            )
        )
    )
    return result.scalar_one_or_none()


def resolve_report_file_path(doc: TenantDocument) -> str | None:
    """Resuelve la ruta del archivo en disco, con fallback por nombre."""
    if doc.file_path and os.path.exists(doc.file_path):
        return doc.file_path
    if doc.file_name:
        fallback = os.path.join(UPLOAD_DIR, doc.file_name)
        if os.path.exists(fallback):
            return fallback
    return None


async def delete_snapshot_report(
    report_id: uuid.UUID, tenant_id, db: AsyncSession
) -> bool:
    """Elimina un informe de BD y disco. Retorna False si no existe."""
    doc = await get_snapshot_report(report_id, tenant_id, db)
    if not doc:
        return False

    for path_candidate in [
        doc.file_path,
        os.path.join(UPLOAD_DIR, doc.file_name) if doc.file_name else None,
    ]:
        if path_candidate and os.path.exists(path_candidate):
            try:
                os.remove(path_candidate)
            except OSError:
                logger.debug("Failed to delete report file from disk: %s", path_candidate, exc_info=True)
            break

    await db.delete(doc)
    await db.commit()
    return True
