"""Endpoints AEAT — custodia de certificado y presentación electrónica de modelos.

Estado: Fase C (preview). La presentación a producción está detrás del flag
`dry_run=true` por defecto. Cambiar a `dry_run=false` solo cuando el cliente
tenga certificado real y haya pasado pruebas en preproducción.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.aeat import (
    CertificateError,
    PresentationError,
    cert_to_dict,
    create_presentation,
    get_active_certificate,
    list_presentations,
    presentation_to_dict,
    revoke_certificate,
    store_certificate,
    submit_presentation,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aeat", tags=["aeat"])


# ─── Certificado ────────────────────────────────────────────────────────────


@router.get("/certificate")
@limiter.limit("30/minute")
async def get_active_cert(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve los metadatos del certificado activo (sin el contenido cifrado)."""
    cert = await get_active_certificate(db, current_user.tenant_id)
    if cert is None:
        return {"active": None}
    return {"active": cert_to_dict(cert)}


@router.post("/certificate/upload", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def upload_cert(
    request: Request,
    file: UploadFile = File(...),
    password: str = Form(...),
    label: str = Form("Certificado representante"),
    notes: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Sube un certificado .pfx/.p12 cifrado. Revoca el anterior si existía."""
    content = await file.read()
    try:
        cert = await store_certificate(
            db, current_user.tenant_id, current_user.id,
            label=label,
            pfx_bytes=content,
            password=password,
            notes=notes,
        )
    except CertificateError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return cert_to_dict(cert)


@router.delete("/certificate/{cert_id}", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def revoke_cert(
    request: Request,
    cert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    try:
        cert = await revoke_certificate(db, current_user.tenant_id, cert_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return cert_to_dict(cert)


# ─── Presentaciones ────────────────────────────────────────────────────────


class _CreatePresentationIn(BaseModel):
    model_code: str
    year: int
    period: str
    xml_unsigned: str
    environment: str = "preproduccion"


@router.post("/presentations", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_presentation_endpoint(
    request: Request,
    payload: _CreatePresentationIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registra una presentación en estado pending con el XML sin firmar."""
    try:
        p = await create_presentation(
            db, current_user.tenant_id, current_user.id,
            model_code=payload.model_code,
            year=payload.year,
            period=payload.period,
            xml_unsigned=payload.xml_unsigned,
            environment=payload.environment,
        )
    except PresentationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return presentation_to_dict(p)


@router.post("/presentations/303-from-quarter", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_303_from_quarter(
    request: Request,
    quarter: int = Query(ge=1, le=4),
    year: int = Query(...),
    environment: str = Query("preproduccion"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atajo: construye el XML del 303 desde las facturas y crea la presentación."""
    from app.services.aeat import (
        build_casillas_303,
        build_modelo_303_xml,
    )
    from app.services.reports.fiscal import build_modelo_303_data

    data = await build_modelo_303_data(db, current_user.tenant_id, quarter, year)
    casillas = build_casillas_303(data)
    xml_str = build_modelo_303_xml(
        tenant_name=data["tenant"]["name"],
        tenant_nif=data["tenant"]["nif"],
        year=year,
        quarter=quarter,
        casillas=casillas,
    )
    try:
        p = await create_presentation(
            db, current_user.tenant_id, current_user.id,
            model_code="303", year=year, period=f"{quarter}T",
            xml_unsigned=xml_str, environment=environment,
        )
    except PresentationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return presentation_to_dict(p)


_QUARTERLY_BUILDERS = {
    "111": "build_modelo_111_data",
    "130": "build_modelo_130_data",
    "115": "build_modelo_115_data",
    "349": "build_modelo_349_data",
}

_YEARLY_BUILDERS = {
    "190": "build_modelo_190_data",
    "347": "build_modelo_347_data",
    "390": "build_modelo_390_data",
}


async def _build_xml_generic(
    db, tenant_id, model_code: str, year: int, period: str, quarter: int | None,
) -> str:
    """Construye XML auxiliar reusando los builders de services.reports.modelos_aeat."""
    from app.services.aeat import build_modelo_xml_generic
    from app.services.reports import modelos_aeat as _ma

    if model_code in _QUARTERLY_BUILDERS:
        builder = getattr(_ma, _QUARTERLY_BUILDERS[model_code])
        if quarter is None:
            raise PresentationError(f"Modelo {model_code} requiere quarter")
        data = await builder(db, tenant_id, quarter, year)
    elif model_code in _YEARLY_BUILDERS:
        builder = getattr(_ma, _YEARLY_BUILDERS[model_code])
        data = await builder(db, tenant_id, year)
    else:
        raise PresentationError(f"Modelo {model_code} sin builder de datos.")

    tenant = data.get("tenant") if isinstance(data, dict) else None
    return build_modelo_xml_generic(
        modelo=model_code, year=year, period=period, data=data,
        tenant_name=(tenant or {}).get("name", ""),
        tenant_nif=(tenant or {}).get("nif", ""),
    )


@router.post("/presentations/quarterly-from-period", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_quarterly_presentation(
    request: Request,
    model_code: str = Query(..., description="111 | 130 | 115 | 349"),
    quarter: int = Query(ge=1, le=4),
    year: int = Query(...),
    environment: str = Query("preproduccion"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atajo para modelos trimestrales (111, 130). Construye XML y crea presentación."""
    if model_code not in _QUARTERLY_BUILDERS:
        raise HTTPException(status_code=400, detail=f"Modelo trimestral no soportado: {model_code}")
    try:
        xml_str = await _build_xml_generic(
            db, current_user.tenant_id, model_code, year, f"{quarter}T", quarter,
        )
        p = await create_presentation(
            db, current_user.tenant_id, current_user.id,
            model_code=model_code, year=year, period=f"{quarter}T",
            xml_unsigned=xml_str, environment=environment,
        )
    except PresentationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return presentation_to_dict(p)


@router.post("/presentations/yearly-from-period", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_yearly_presentation(
    request: Request,
    model_code: str = Query(..., description="190 | 347 | 390"),
    year: int = Query(...),
    environment: str = Query("preproduccion"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atajo para modelos anuales (190, 347, 390)."""
    if model_code not in _YEARLY_BUILDERS:
        raise HTTPException(status_code=400, detail=f"Modelo anual no soportado: {model_code}")
    try:
        xml_str = await _build_xml_generic(
            db, current_user.tenant_id, model_code, year, "A", None,
        )
        p = await create_presentation(
            db, current_user.tenant_id, current_user.id,
            model_code=model_code, year=year, period="A",
            xml_unsigned=xml_str, environment=environment,
        )
    except PresentationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return presentation_to_dict(p)


@router.post("/presentations/{presentation_id}/submit")
@limiter.limit("5/minute")
async def submit_presentation_endpoint(
    request: Request,
    presentation_id: UUID,
    dry_run: bool = Query(True, description="Si true, no se envía a la SEDE; respuesta simulada."),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Firma + envía la presentación. Por defecto dry-run (sin POST real)."""
    try:
        p = await submit_presentation(
            db, current_user.tenant_id, presentation_id, dry_run=dry_run,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PresentationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return presentation_to_dict(p)


@router.get("/presentations")
@limiter.limit("30/minute")
async def list_presentations_endpoint(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await list_presentations(db, current_user.tenant_id, limit=limit)
    return {"items": [presentation_to_dict(p) for p in items]}
