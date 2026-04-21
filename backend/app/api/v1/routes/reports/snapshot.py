"""Company snapshot GET + POST generate + report management (list, download, delete)."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.services.documents.snapshot import (
    delete_snapshot_report,
    get_snapshot_report,
    get_tenant_name,
    list_snapshot_reports,
    resolve_report_file_path,
    save_snapshot_report,
)
from app.services.pdf import generate_snapshot_pdf
from app.services.reports import aggregate, parse_month

from ._schemas import CompanySnapshot, ReportOut

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
        month = date.today().strftime("%Y-%m")

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
        month = date.today().strftime("%Y-%m")

    try:
        start, end = parse_month(month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    company_name = await get_tenant_name(current_user.tenant_id, db)
    snap = await aggregate(db, current_user.tenant_id, start, end)

    pdf_bytes = generate_snapshot_pdf(
        snap=snap.model_dump(),
        company_name=company_name,
        month=month,
    )

    return await save_snapshot_report(
        pdf_bytes=pdf_bytes,
        month=month,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        executive_summary=snap.resumen_ejecutivo,
        db=db,
    )


@router.get("/", response_model=list[ReportOut])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos los informes mensuales generados para este tenant."""
    return await list_snapshot_reports(current_user.tenant_id, db)


@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descarga el PDF de un informe."""
    doc = await get_snapshot_report(report_id, current_user.tenant_id, db)
    if not doc:
        raise HTTPException(status_code=404, detail="Informe no encontrado")

    file_path = resolve_report_file_path(doc)
    if not file_path:
        raise HTTPException(
            status_code=404, detail=f"Archivo no disponible (ruta: {doc.file_path})"
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
    deleted = await delete_snapshot_report(report_id, current_user.tenant_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    return {"status": "deleted", "id": str(report_id)}
