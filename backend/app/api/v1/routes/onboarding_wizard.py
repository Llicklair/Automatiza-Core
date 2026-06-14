"""Rutas REST del wizard onboarding focado (UI.ONB)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import User
from app.services.onboarding.simulate_303 import simulate_modelo_303
from app.services.onboarding.wizard import (
    reset,
    set_step,
    skip_to_end,
    sync_llm_config_step,
    to_dict,
)

router = APIRouter(prefix="/onboarding/wizard", tags=["onboarding"])


class WizardStateOut(BaseModel):
    step_company: bool
    step_cert: bool
    step_data: bool
    step_use_case: bool
    step_llm_config: bool
    completed_at: str | None
    skipped_at: str | None
    is_dismissed: bool


@router.get("", response_model=WizardStateOut)
async def get_wizard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Devuelve el estado actual del wizard del tenant.

    Auto-sincroniza el paso BYOK (`llm_config`) desde la readiness real de IA
    antes de devolver, para que refleje si el tenant ya configuró su clave.
    """
    record = await sync_llm_config_step(db, tenant_id=user.tenant_id)
    await db.commit()
    return to_dict(record)


class SetStepIn(BaseModel):
    step: Literal["company", "cert", "data", "use_case", "llm_config"]
    value: bool


@router.patch("", response_model=WizardStateOut)
async def patch_step(
    payload: SetStepIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Marca un paso como completado o pendiente."""
    try:
        record = await set_step(
            db,
            tenant_id=user.tenant_id,
            step=payload.step,
            value=payload.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return to_dict(record)


@router.post("/skip", response_model=WizardStateOut)
async def post_skip(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Marca el wizard como saltado por el usuario."""
    record = await skip_to_end(db, tenant_id=user.tenant_id)
    await db.commit()
    return to_dict(record)


@router.get("/simulate/303")
async def get_simulate_303(
    quarter: int = 1,
    year: int = 2026,
    user: User = Depends(get_current_user),
) -> dict:
    """UI.SIM — simulación Modelo 303 con datos ejemplo (sin BD del tenant).

    Diseñado para el último paso del wizard onboarding: el usuario ve un
    303 calculado sobre un dataset de un autónomo prototípico antes de
    meter sus propios datos.
    """
    try:
        return simulate_modelo_303(quarter=quarter, year=year)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset", response_model=WizardStateOut)
async def post_reset(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reinicia el wizard — útil para re-onboarding."""
    record = await reset(db, tenant_id=user.tenant_id)
    await db.commit()
    return to_dict(record)
