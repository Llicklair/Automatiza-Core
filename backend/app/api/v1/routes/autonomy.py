"""Rutas REST de política de autonomía (SEC.AUT)."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.base import get_db
from app.db.models.auth import User
from app.services.autonomy import (
    KNOWN_DOMAINS,
    list_policies,
    reset_policy,
    set_policy,
)

router = APIRouter(prefix="/autonomy", tags=["autonomy"])
logger = logging.getLogger("autonomy")

_admin_only = Depends(require_role("admin"))

AutonomyMode = Literal["AUTO", "CONFIRM", "MANUAL"]


class PolicyEntry(BaseModel):
    mode: AutonomyMode
    is_default: bool
    locked: bool = False  # dominios con modo forzado (fiscal) — no editables


class PolicyListOut(BaseModel):
    policies: dict[str, PolicyEntry]
    known_domains: list[str]


@router.get("", response_model=PolicyListOut)
async def get_all_policies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Devuelve todas las policies efectivas del tenant."""
    policies = await list_policies(db, tenant_id=user.tenant_id)
    return {
        "policies": policies,
        "known_domains": sorted(KNOWN_DOMAINS),
    }


class SetPolicyIn(BaseModel):
    mode: AutonomyMode = Field(..., description="AUTO | CONFIRM | MANUAL")


@router.put(
    "/{domain}",
    response_model=PolicyEntry,
    dependencies=[_admin_only],
)
async def put_policy(
    domain: str,
    payload: SetPolicyIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Configura el mode para un dominio. Solo admin."""
    try:
        record = await set_policy(
            db,
            tenant_id=user.tenant_id,
            domain=domain,
            mode=payload.mode,
            updated_by=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return {"mode": record.mode, "is_default": False}


@router.delete(
    "/{domain}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin_only],
)
async def delete_policy(
    domain: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resetea el dominio al default — borra la fila persistida."""
    try:
        await reset_policy(db, tenant_id=user.tenant_id, domain=domain)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
