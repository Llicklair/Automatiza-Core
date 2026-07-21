"""Rutas REST de configuración del modo Verifactu (FAC.MODE)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.base import get_db
from app.db.models.auth import User
from app.services.billing.declaracion_responsable import generate_declaracion_responsable
from app.services.billing.verifactu_mode import (
    VerifactuMode,
    get_config,
    set_mode,
    to_dict,
)

router = APIRouter(prefix="/verifactu/config", tags=["verifactu"])

_admin_only = Depends(require_role("admin"))


class VerifactuConfigOut(BaseModel):
    mode: Literal["voluntary", "no_remission"]
    updated_at: str
    is_default: bool


@router.get("", response_model=VerifactuConfigOut)
async def get_endpoint(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Devuelve el modo Verifactu del tenant."""
    record = await get_config(db, tenant_id=user.tenant_id)
    await db.commit()
    return to_dict(record)


class SetModeIn(BaseModel):
    mode: VerifactuMode  # type: ignore[valid-type]


@router.put(
    "",
    response_model=VerifactuConfigOut,
    dependencies=[_admin_only],
)
async def put_endpoint(
    payload: SetModeIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Configura el modo Verifactu del tenant. Solo admin."""
    try:
        record = await set_mode(
            db,
            tenant_id=user.tenant_id,
            mode=payload.mode,
            updated_by=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await db.commit()
    return to_dict(record)


@router.get("/export", dependencies=[_admin_only])
async def export_endpoint(
    desde: str,
    hasta: str,
    formato: Literal["json", "xml"] = "json",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Exportación/volcado de los registros de facturación (y eventos) del
    periodo — art. 8.2.c RD 1007/2023 y anexo ap. 3. Registra el evento
    EXPORTACION en la cadena. Fechas `YYYY-MM-DD`; `hasta` inclusivo. Solo admin."""
    import json
    from datetime import datetime

    from app.services.billing.verifactu_export import export_periodo, export_periodo_xml

    try:
        d = datetime.fromisoformat(desde)
        h = datetime.fromisoformat(hasta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Fechas inválidas: usa YYYY-MM-DD") from e
    if "T" not in hasta:
        h = h.replace(hour=23, minute=59, second=59)  # día final inclusivo
    if h < d:
        raise HTTPException(status_code=400, detail="'hasta' debe ser posterior a 'desde'")

    try:
        if formato == "xml":
            contenido = await export_periodo_xml(db, tenant_id=user.tenant_id, desde=d, hasta=h)
            media = "application/xml; charset=utf-8"
            ext = "xml"
        else:
            data = await export_periodo(db, tenant_id=user.tenant_id, desde=d, hasta=h)
            contenido = json.dumps(data, ensure_ascii=False, indent=2, default=str)
            media = "application/json; charset=utf-8"
            ext = "json"
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await db.commit()  # persiste el evento EXPORTACION registrado por el servicio
    return Response(
        content=contenido,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="verifactu-export-{desde}-a-{hasta}.{ext}"'},
    )


@router.get("/declaracion-responsable", dependencies=[_admin_only])
async def declaracion_responsable_endpoint() -> Response:
    """Documento de la declaración responsable del productor del SIF (art. 15 Orden
    HAC/1177/2024), disponible dentro del sistema (art. 15.3). Solo admin."""
    from app.core.config import settings

    lugar = getattr(settings, "VERIFACTU_SIF_LUGAR", None) or "España"
    direccion = getattr(settings, "VERIFACTU_SIF_DIRECCION", None) or ""
    doc = generate_declaracion_responsable(lugar=lugar, direccion_productor=direccion)
    return Response(content=doc, media_type="text/plain; charset=utf-8")
