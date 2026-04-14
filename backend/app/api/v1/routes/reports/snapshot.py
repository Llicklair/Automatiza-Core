"""Company snapshot GET + POST generate + report management (list, download, delete)."""

import logging
import os
import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Tenant, TenantDocument, User
from app.services.pdf import generate_snapshot_pdf

from app.services.reports import aggregate, parse_month

from ._schemas import CompanySnapshot, ReportOut

UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "uploads")
)

_logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/company-snapshot", response_model=CompanySnapshot)
async def get_company_snapshot(
    month: str = Query(
        default=None, description="Mes en formato YYYY-MM. Por defecto: mes actual."
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el snapshot agregado de la empresa para el mes indicado (sin generar PDF)."""
    if not month:
        today = date.today()
        month = today.strftime("%Y-%m")

    try:
        start, end = parse_month(month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return await aggregate(db, current_user.tenant_id, start, end)


@router.post("/company-snapshot/generate", response_model=ReportOut, status_code=201)
async def generate_company_snapshot_pdf(
    month: str = Query(
        default=None, description="Mes en formato YYYY-MM. Por defecto: mes actual."
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera el informe mensual PDF y lo guarda en documentos del tenant."""
    if not month:
        today = date.today()
        month = today.strftime("%Y-%m")

    try:
        start, end = parse_month(month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Obtener nombre de la empresa
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_q.scalar_one_or_none()
    company_name = tenant.name if tenant and tenant.name else "Tu empresa"

    snap = await aggregate(db, current_user.tenant_id, start, end)

    # Generar PDF con gráficas
    pdf_bytes = generate_snapshot_pdf(
        snap=snap.model_dump(),
        company_name=company_name,
        month=month,
    )

    # Guardar a disco
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_name = f"informe_{month}_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    with open(file_path, "wb") as fh:
        fh.write(pdf_bytes)

    # Persistir en tenant_documents
    doc = TenantDocument(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.id,
        file_name=file_name,
        file_type="application/pdf",
        file_path=file_path,
        file_size=len(pdf_bytes),
        status="processed",
        parsed_content=snap.resumen_ejecutivo,
        category="informes",
        created_at=datetime.now(UTC),
        processed_at=datetime.now(UTC),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/", response_model=list[ReportOut])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos los informes mensuales generados para este tenant."""
    q = await db.execute(
        select(TenantDocument)
        .where(
            and_(
                TenantDocument.tenant_id == current_user.tenant_id,
                TenantDocument.category == "informes",
            )
        )
        .order_by(TenantDocument.created_at.desc())
    )
    return q.scalars().all()


@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descarga el PDF de un informe."""
    q = await db.execute(
        select(TenantDocument).where(
            and_(
                TenantDocument.id == report_id,
                TenantDocument.tenant_id == current_user.tenant_id,
                TenantDocument.category == "informes",
            )
        )
    )
    doc = q.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Informe no encontrado")

    # Resolver ruta del archivo — fallback si la ruta guardada es obsoleta
    file_path = doc.file_path
    if not file_path or not os.path.exists(file_path):
        # Intentar encontrar por nombre en UPLOAD_DIR
        fallback = os.path.join(UPLOAD_DIR, doc.file_name) if doc.file_name else None
        if fallback and os.path.exists(fallback):
            file_path = fallback
        else:
            raise HTTPException(
                status_code=404, detail=f"Archivo no disponible (ruta: {file_path})"
            )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=doc.file_name,
    )


@router.delete("/{report_id}", status_code=200)
async def delete_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina un informe: borra archivo de disco y registro de BD."""
    q = await db.execute(
        select(TenantDocument).where(
            and_(
                TenantDocument.id == report_id,
                TenantDocument.tenant_id == current_user.tenant_id,
                TenantDocument.category == "informes",
            )
        )
    )
    doc = q.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Informe no encontrado")

    # Borrar archivo de disco
    for path_candidate in [
        doc.file_path,
        os.path.join(UPLOAD_DIR, doc.file_name) if doc.file_name else None,
    ]:
        if path_candidate and os.path.exists(path_candidate):
            try:
                os.remove(path_candidate)
            except OSError:
                _logger.debug(
                    "Failed to delete report file from disk: %s", path_candidate, exc_info=True
                )
            break

    await db.delete(doc)
    await db.commit()
    return {"status": "deleted", "id": str(report_id)}
