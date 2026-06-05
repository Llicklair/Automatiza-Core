"""Rutas de inteligencia de cobros (F3.9) — ranking de riesgo + recordatorios."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import User
from app.middleware.rate_limit import limiter
from app.services.collections import (
    invoices_due_for_reminder,
    rank_tenant_collections,
)

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("/risk")
@limiter.limit("30/minute")
async def get_collections_risk(
    request: Request,
    only_with_outstanding: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ranking de clientes por riesgo de cobro (heurística sobre histórico)."""
    scores = await rank_tenant_collections(
        db,
        current_user.tenant_id,
        only_with_outstanding=only_with_outstanding,
    )
    return {
        "count": len(scores),
        "high_risk_count": sum(1 for s in scores if s.risk_level == "high"),
        "total_outstanding": round(sum(s.overdue_amount for s in scores), 2),
        "clients": [s.to_dict() for s in scores],
    }


@router.get("/due-reminders")
@limiter.limit("30/minute")
async def get_due_reminders(
    request: Request,
    fire_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista de recordatorios planificados para hoy (o `fire_date` si se pasa).

    Pensado para que un cron diario lo invoque y envíe los emails.
    """
    steps = await invoices_due_for_reminder(
        db, current_user.tenant_id, today=fire_date
    )
    return {
        "fire_date": (fire_date or date.today()).isoformat(),
        "count": len(steps),
        "steps": [s.to_dict() for s in steps],
    }
