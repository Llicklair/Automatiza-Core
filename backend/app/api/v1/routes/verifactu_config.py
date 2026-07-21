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


@router.get("/declaracion-responsable", dependencies=[_admin_only])
async def declaracion_responsable_endpoint() -> Response:
    """Documento de la declaración responsable del productor del SIF (art. 15 Orden
    HAC/1177/2024), disponible dentro del sistema (art. 15.3). Solo admin."""
    from app.core.config import settings

    lugar = getattr(settings, "VERIFACTU_SIF_LUGAR", None) or "España"
    direccion = getattr(settings, "VERIFACTU_SIF_DIRECCION", None) or ""
    doc = generate_declaracion_responsable(lugar=lugar, direccion_productor=direccion)
    return Response(content=doc, media_type="text/plain; charset=utf-8")
