"""Rutas para alertas automáticas."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.alerts.service import check_and_alert_tenant, get_recent_alerts

router = APIRouter()


@router.get("", tags=["alerts"])
@limiter.limit("30/minute")
async def list_alerts(
    request: Request,
    hours: int = 48,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = await get_recent_alerts(db, current_user.tenant_id, hours=hours)
    return [
        {
            "id": str(log.id),
            "alert_type": log.alert_type,
            "entity_id": log.entity_id,
            "entity_label": log.entity_label,
            "severity": log.severity,
            "sent_at": log.sent_at.isoformat(),
        }
        for log in logs
    ]


@router.post("/check", tags=["alerts"])
@limiter.limit("5/minute")
async def trigger_check(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lanza una comprobación manual inmediata para el tenant actual."""
    count = await check_and_alert_tenant(db, current_user.tenant_id)
    return {"new_alerts": count, "message": f"Comprobación completada — {count} alertas nuevas"}
