"""Fiscal snapshot GET + POST generate + modelo 303 + libro registro endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_tenant_or_404
from app.db.base import get_db
from app.db.models.models import Tenant, User
from app.services.pdf import generate_modelo_303_pdf
from app.services.pdf_reports import save_fiscal_report_to_db
from app.services.reports import (
    aggregate_fiscal,
    build_libro_registro_csv,
    build_modelo_303_data,
    parse_period,
)

from ._schemas import FiscalSnapshot, ReportOut

router = APIRouter()


@router.get("/fiscal-snapshot", response_model=FiscalSnapshot)
async def get_fiscal_snapshot(
    period: str = Query(
        default=None, description="Periodo: YYYY-MM (mensual) o YYYY-Q1..Q4 (trimestral)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el snapshot fiscal para el periodo indicado."""
    if not period:
        today = date.today()
        period = today.strftime("%Y-%m")

    try:
        start, end, label = parse_period(period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return await aggregate_fiscal(db, current_user.tenant_id, start, end, period, label)


@router.post("/fiscal-snapshot/generate", response_model=ReportOut, status_code=201)
async def generate_fiscal_snapshot_pdf(
    period: str = Query(default=None, description="Periodo: YYYY-MM o YYYY-Q1..Q4"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_or_404),
):
    """Genera el informe fiscal PDF y lo guarda en documentos del tenant."""
    if not period:
        today = date.today()
        period = today.strftime("%Y-%m")

    try:
        start, end, label = parse_period(period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    company_name = tenant.name if tenant.name else "Tu empresa"

    snap = await aggregate_fiscal(db, current_user.tenant_id, start, end, period, label)

    from app.services.pdf_reports import generate_fiscal_report_pdf

    pdf_bytes = generate_fiscal_report_pdf(
        snap=snap.model_dump(),
        company_name=company_name,
        period=period,
    )

    doc = await save_fiscal_report_to_db(
        pdf_bytes=pdf_bytes,
        period=period,
        resumen_ejecutivo=snap.resumen_ejecutivo,
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.id,
        db=db,
    )
    return doc


@router.get("/modelo-303")
async def generate_modelo_303(
    quarter: int = Query(ge=1, le=4, description="Trimestre (1-4)"),
    year: int = Query(default=2026, description="Ano fiscal"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera borrador PDF del Modelo 303 (liquidacion trimestral de IVA)."""
    data = await build_modelo_303_data(db, current_user.tenant_id, quarter, year)
    pdf_bytes = generate_modelo_303_pdf(data)
    file_name = f"Modelo303_Q{quarter}_{year}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/modelo-303/expediente")
async def get_modelo_303_expediente(
    quarter: int = Query(ge=1, le=4, description="Trimestre (1-4)"),
    year: int = Query(default=2026, description="Año fiscal"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Expediente listo para presentar el 303 en la SEDE AEAT.

    Devuelve casillas oficiales rellenadas + XML auxiliar + checklist de pasos
    a seguir + URL al PDF. NO presenta a la SEDE (eso requiere certificado del
    declarante; ver Fase C del roadmap).
    """
    from app.services.aeat import build_expediente_303

    return await build_expediente_303(db, current_user.tenant_id, quarter, year)


@router.get("/libro-registro")
async def export_libro_registro(
    year: int = Query(description="Ano fiscal (p.ej. 2026)"),
    type: str = Query(default="emitidas", description="Tipo: 'emitidas' o 'recibidas'"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta el libro de registro de facturas emitidas/recibidas en formato CSV (AEAT)."""
    csv_content, file_name = await build_libro_registro_csv(
        db,
        current_user.tenant_id,
        year,
        type,
    )
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
