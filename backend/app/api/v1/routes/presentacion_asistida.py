"""Rutas REST de presentación asistida AEAT (PRES.ASS)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import Tenant, User
from app.services.presentacion.asistida import (
    TenantSummary,
    build_xml,
    get_sede_link,
)

router = APIRouter(prefix="/presentacion/asistida", tags=["presentacion"])


@router.get("/info/{modelo}")
async def get_info(
    modelo: Literal["131", "200"],
    user: User = Depends(get_current_user),
) -> dict:
    """Devuelve el deep-link Sede AEAT + metadatos del modelo asistido."""
    try:
        link = get_sede_link(modelo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    descriptions = {
        "131": "IRPF — Estimación objetiva (módulos). Trimestral.",
        "200": "Impuesto sobre Sociedades. Anual.",
    }
    return {
        "modelo": modelo,
        "descripcion": descriptions[modelo],
        "sede_url": link,
        "asistido": True,
        "presentacion_automatica": False,
    }


@router.get("/xml/{modelo}")
async def download_xml(
    modelo: Literal["131", "200"],
    ejercicio: int | None = Query(default=None, ge=2020, le=2099),
    trimestre: int | None = Query(default=None, ge=1, le=4),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Genera y devuelve un XML pre-rellenado del modelo asistido.

    El usuario importa el archivo en Sede AEAT (Predeclaración) y allí
    completa los datos que falten antes de presentar.
    """
    if modelo not in ("131", "200"):
        raise HTTPException(status_code=400, detail=f"Modelo no soportado: {modelo}")

    tenant_q = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_q.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    year = ejercicio or datetime.now(UTC).year
    summary = TenantSummary(
        nif=tenant.nif or "",
        name=tenant.name or "",
        address=tenant.address or "",
        fiscal_year=year,
        quarter=trimestre if modelo == "131" else None,
    )

    xml = build_xml(modelo, summary)
    period_tag = f"{year}-Q{trimestre or 1}" if modelo == "131" else f"{year}"
    filename = f"modelo{modelo}-prerelleno-{period_tag}.xml"

    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
