"""Rutas de métricas de valor (centro de mando) — thin controller."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import User
from app.middleware.rate_limit import limiter
from app.services.metrics.time_saved import time_saved_summary

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/time-saved")
@limiter.limit("30/minute")
async def get_time_saved(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tiempo ahorrado por la IA en el periodo (estimación desde AuditLog)."""
    return await time_saved_summary(db, current_user.tenant_id, days=days)
