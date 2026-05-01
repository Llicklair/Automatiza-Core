"""Analytics dashboard endpoint — single aggregated source for the /analitica page."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.analytics import get_dashboard
from app.services.reports import parse_month

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
@limiter.limit("30/minute")
async def get_analytics_dashboard(
    request: Request,
    period: str = Query(
        default=None,
        description="Periodo en formato YYYY-MM. Por defecto: mes actual.",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el snapshot agregado del dashboard analítico para el periodo indicado."""
    if not period:
        period = date.today().strftime("%Y-%m")

    try:
        start, end = parse_month(period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return await get_dashboard(db, current_user.tenant_id, period, start, end)
