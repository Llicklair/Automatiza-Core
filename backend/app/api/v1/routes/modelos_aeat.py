"""Rutas REST para generación de Modelos AEAT calculados (MOD.130/347/390/111/190).

Cada endpoint devuelve el dict de liquidación pre-calculado a partir de los
datos del tenant en el rango (ejercicio, trimestre). El frontend `/impuestos`
muestra estas cifras como preview antes de presentar (manual o asistido).

No firma ni presenta — solo calcula y expone. La presentación real corre via:
  - 303/130/347/390/111/190 → PRES.303 + PRES.MOD1/MOD2 (post-DEC.14)
  - 131/200 → PRES.ASS (XML pre-rellenado, presentación manual en Sede)
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import User
from app.services.reports.modelos_aeat import (
    build_modelo_111_data,
    build_modelo_115_data,
    build_modelo_130_data,
    build_modelo_190_data,
    build_modelo_200_data,
    build_modelo_347_data,
    build_modelo_349_data,
    build_modelo_390_data,
)

router = APIRouter(prefix="/reports/modelos", tags=["modelos_aeat"])


def _current_year() -> int:
    return datetime.now(UTC).year


@router.get("/130")
async def get_modelo_130(
    quarter: int = Query(..., ge=1, le=4),
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Modelo 130 — IRPF fraccionado (estimación directa), trimestral."""
    y = year or _current_year()
    return await build_modelo_130_data(db, user.tenant_id, quarter, y)


@router.get("/111")
async def get_modelo_111(
    quarter: int = Query(..., ge=1, le=4),
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Modelo 111 — Retenciones trabajadores, trimestral."""
    y = year or _current_year()
    return await build_modelo_111_data(db, user.tenant_id, quarter, y)


@router.get("/190")
async def get_modelo_190(
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Modelo 190 — Resumen anual retenciones (4×111)."""
    y = year or _current_year()
    return await build_modelo_190_data(db, user.tenant_id, y)


@router.get("/347")
async def get_modelo_347(
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Modelo 347 — Operaciones con terceros >3.005,06€, anual."""
    y = year or _current_year()
    return await build_modelo_347_data(db, user.tenant_id, y)


@router.get("/390")
async def get_modelo_390(
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Modelo 390 — Resumen anual IVA (4×303)."""
    y = year or _current_year()
    return await build_modelo_390_data(db, user.tenant_id, y)


@router.get("/200")
async def get_modelo_200(
    year: int = Query(default=None),
    tipo_impositivo_pct: float | None = Query(default=None, ge=0, le=100),
    pagos_fraccionados_pagados: float = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Modelo 200 — Impuesto sobre Sociedades (preview anual)."""
    y = year or (_current_year() - 1)  # por defecto, ejercicio anterior cerrado
    return await build_modelo_200_data(
        db,
        user.tenant_id,
        y,
        tipo_impositivo_pct=tipo_impositivo_pct,
        pagos_fraccionados_pagados=pagos_fraccionados_pagados,
    )


@router.get("/preventive-check")
async def get_preventive_check(
    quarter: int = Query(..., ge=1, le=4),
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Asistente fiscal preventivo — detecta riesgos del trimestre antes
    de cerrar el 303. Cruza facturas emitidas y recibidas con el simulador
    y devuelve hallazgos accionables (NIF de proveedor faltante, facturas
    descuadradas, drafts olvidados, Verifactu sin registro, etc.).
    """
    from app.services.aeat.preventive_check import check_quarter

    y = year or _current_year()
    findings = await check_quarter(db, user.tenant_id, quarter, y)
    return {
        "quarter": quarter,
        "year": y,
        "findings": [f.to_dict() for f in findings],
        "count_by_severity": {
            "high": sum(1 for f in findings if f.severity == "high"),
            "medium": sum(1 for f in findings if f.severity == "medium"),
            "low": sum(1 for f in findings if f.severity == "low"),
        },
    }


# ── Descarga de PDF borrador imprimible por modelo ────────────────────────────

def _pdf_response(pdf: bytes, filename: str) -> Response:
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/303/pdf")
async def download_modelo_303_pdf(
    quarter: int = Query(..., ge=1, le=4),
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """PDF borrador imprimible del Modelo 303 (IVA trimestral)."""
    from app.services.pdf_reports import generate_modelo_303_pdf
    from app.services.reports.fiscal import build_modelo_303_data

    y = year or _current_year()
    data = await build_modelo_303_data(db, user.tenant_id, quarter, y)
    return _pdf_response(generate_modelo_303_pdf(data), f"modelo-303-{quarter}T-{y}.pdf")


@router.get("/130/pdf")
async def download_modelo_130_pdf(
    quarter: int = Query(..., ge=1, le=4),
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """PDF borrador imprimible del Modelo 130 (IRPF pago fraccionado)."""
    from app.services.pdf_reports import generate_modelo_130_pdf

    y = year or _current_year()
    data = await build_modelo_130_data(db, user.tenant_id, quarter, y)
    return _pdf_response(generate_modelo_130_pdf(data), f"modelo-130-{quarter}T-{y}.pdf")


@router.get("/111/pdf")
async def download_modelo_111_pdf(
    quarter: int = Query(..., ge=1, le=4),
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """PDF borrador imprimible del Modelo 111 (retenciones del trabajo)."""
    from app.services.pdf_reports import generate_modelo_111_pdf

    y = year or _current_year()
    data = await build_modelo_111_data(db, user.tenant_id, quarter, y)
    return _pdf_response(generate_modelo_111_pdf(data), f"modelo-111-{quarter}T-{y}.pdf")


@router.get("/190/pdf")
async def download_modelo_190_pdf(
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """PDF borrador imprimible del Modelo 190 (resumen anual de retenciones)."""
    from app.services.pdf_reports import generate_modelo_190_pdf

    y = year or _current_year()
    data = await build_modelo_190_data(db, user.tenant_id, y)
    return _pdf_response(generate_modelo_190_pdf(data), f"modelo-190-{y}.pdf")


@router.get("/347/pdf")
async def download_modelo_347_pdf(
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """PDF borrador imprimible del Modelo 347 (operaciones con terceros)."""
    from app.services.pdf_reports import generate_modelo_347_pdf

    y = year or _current_year()
    data = await build_modelo_347_data(db, user.tenant_id, y)
    return _pdf_response(generate_modelo_347_pdf(data), f"modelo-347-{y}.pdf")


@router.get("/390/pdf")
async def download_modelo_390_pdf(
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """PDF borrador imprimible del Modelo 390 (resumen anual de IVA)."""
    from app.services.pdf_reports import generate_modelo_390_pdf

    y = year or _current_year()
    data = await build_modelo_390_data(db, user.tenant_id, y)
    return _pdf_response(generate_modelo_390_pdf(data), f"modelo-390-{y}.pdf")


@router.get("/115/pdf")
async def download_modelo_115_pdf(
    quarter: int = Query(..., ge=1, le=4),
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """PDF borrador imprimible del Modelo 115 (retenciones por alquiler)."""
    from app.services.pdf_reports import generate_modelo_115_pdf

    y = year or _current_year()
    data = await build_modelo_115_data(db, user.tenant_id, quarter, y)
    return _pdf_response(generate_modelo_115_pdf(data), f"modelo-115-{quarter}T-{y}.pdf")


@router.get("/349/pdf")
async def download_modelo_349_pdf(
    quarter: int = Query(..., ge=1, le=4),
    year: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """PDF borrador imprimible del Modelo 349 (operaciones intracomunitarias)."""
    from app.services.pdf_reports import generate_modelo_349_pdf

    y = year or _current_year()
    data = await build_modelo_349_data(db, user.tenant_id, quarter, y)
    return _pdf_response(generate_modelo_349_pdf(data), f"modelo-349-{quarter}T-{y}.pdf")
