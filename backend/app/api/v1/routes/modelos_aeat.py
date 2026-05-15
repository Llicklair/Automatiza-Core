"""Rutas REST para generación de Modelos AEAT calculados (MOD.130/347/390/111/190).

Cada endpoint devuelve el dict de liquidación pre-calculado a partir de los
datos del tenant en el rango (ejercicio, trimestre). El frontend `/impuestos`
muestra estas cifras como preview antes de presentar (manual o asistido).

No firma ni presenta — solo calcula y expone. La presentación real corre via:
  - 303/130/347/390/111/190 → PRES.303 + PRES.MOD1/MOD2 (post-DEC.14)
  - 131/200 → PRES.ASS (XML pre-rellenado, presentación manual en Sede)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import User
from app.services.reports.modelos_aeat import (
    build_modelo_111_data,
    build_modelo_130_data,
    build_modelo_190_data,
    build_modelo_347_data,
    build_modelo_390_data,
)

router = APIRouter(prefix="/reports/modelos", tags=["modelos_aeat"])


def _current_year() -> int:
    return datetime.now(timezone.utc).year


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
