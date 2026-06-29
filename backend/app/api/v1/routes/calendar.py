"""Calendario unificado — agrega eventos de múltiples módulos."""
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.calendar_service import get_unified_calendar

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/unified")
@limiter.limit("60/minute")
async def unified_calendar(
    request: Request,
    start: date = Query(..., description="Fecha inicio YYYY-MM-DD"),
    end: date = Query(..., description="Fecha fin YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve todos los eventos del rango [start, end] agrupados de todos los módulos."""
    return await get_unified_calendar(db, current_user.tenant_id, start, end)
