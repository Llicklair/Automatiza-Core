"""Rutas REST del wizard REGAP (PRES.REG)."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.base import get_db
from app.db.models.auth import User
from app.services.onboarding.regap import (
    AuthMethod,
    get_regap_status,
    mark_power_granted,
    reset_regap,
    start_identification,
    verify_regap_consulta,
)

router = APIRouter(prefix="/onboarding/regap", tags=["onboarding"])
logger = logging.getLogger("onboarding.regap")

_admin_only = Depends(require_role("admin"))


class RegapStatusOut(BaseModel):
    status: Literal[
        "not_started",
        "identifying",
        "cert_pending",
        "power_granted",
        "verified",
        "rejected",
    ]
    auth_method: Literal["clave_pin", "clave_permanente", "cert_fnmt"] | None
    apoderado_nif: str | None
    apoderado_nombre: str | None
    verified_at: str | None
    rejected_reason: str | None


def _to_out(record) -> dict:
    return {
        "status": record.status,
        "auth_method": record.auth_method,
        "apoderado_nif": record.apoderado_nif,
        "apoderado_nombre": record.apoderado_nombre,
        "verified_at": record.verified_at.isoformat() if record.verified_at else None,
        "rejected_reason": record.rejected_reason,
    }


@router.get("", response_model=RegapStatusOut)
async def get_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Devuelve el estado actual del wizard REGAP del tenant."""
    record = await get_regap_status(db, tenant_id=user.tenant_id)
    await db.commit()
    return _to_out(record)


class StartIdentificationIn(BaseModel):
    auth_method: AuthMethod = Field(..., description="clave_pin | clave_permanente | cert_fnmt")


@router.post(
    "/start",
    response_model=RegapStatusOut,
    dependencies=[_admin_only],
)
async def post_start(
    payload: StartIdentificationIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Step 1 → 2: usuario eligió método de autenticación en el wizard."""
    try:
        record = await start_identification(
            db,
            tenant_id=user.tenant_id,
            auth_method=payload.auth_method,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    await db.commit()
    return _to_out(record)


@router.post(
    "/grant",
    response_model=RegapStatusOut,
    dependencies=[_admin_only],
)
async def post_grant(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Step 2 → 3: el usuario declara haber completado el apoderamiento en Sede AEAT."""
    try:
        record = await mark_power_granted(db, tenant_id=user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    await db.commit()
    return _to_out(record)


class VerifyIn(BaseModel):
    nif_cliente: str = Field(..., min_length=8, max_length=20)


@router.post(
    "/verify",
    response_model=RegapStatusOut,
    dependencies=[_admin_only],
)
async def post_verify(
    payload: VerifyIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Step 3 → 4: consulta REGAP confirma el apoderamiento (mocked v1.0)."""
    try:
        record = await verify_regap_consulta(
            db,
            tenant_id=user.tenant_id,
            nif_cliente=payload.nif_cliente,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    await db.commit()
    return _to_out(record)


@router.post(
    "/reset",
    response_model=RegapStatusOut,
    dependencies=[_admin_only],
)
async def post_reset(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Vuelve a `not_started` — útil para reintentar con otro método."""
    record = await reset_regap(db, tenant_id=user.tenant_id)
    await db.commit()
    return _to_out(record)
