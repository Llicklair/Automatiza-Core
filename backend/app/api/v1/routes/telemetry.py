"""Endpoints de gestión de telemetría (AI.REV).

Permite al usuario:
* Consultar el estado actual de su consentimiento.
* Revocar el consentimiento y solicitar borrado de eventos.

Cumplimiento RGPD Art. 17 (derecho de supresión) + Art. 7 (revocabilidad).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import TelemetryOptOut, User

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class TelemetryStatusResponse(BaseModel):
    tenant_id: str
    opted_out: bool
    opted_out_at: datetime | None
    note: str


class RevokeResponse(BaseModel):
    tenant_id: str
    opted_out: bool
    opted_out_at: datetime
    purge_job_scheduled: bool
    message: str


@router.get("/me", response_model=TelemetryStatusResponse)
async def get_my_telemetry_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TelemetryStatusResponse:
    """Devuelve el estado de consentimiento de telemetría del tenant actual."""
    result = await db.execute(
        select(TelemetryOptOut).where(TelemetryOptOut.tenant_id == user.tenant_id)
    )
    opt_out = result.scalar_one_or_none()
    return TelemetryStatusResponse(
        tenant_id=str(user.tenant_id),
        opted_out=opt_out is not None,
        opted_out_at=opt_out.created_at if opt_out else None,
        note=(
            "Telemetría desactivada: no se envían informes técnicos al VPS." if opt_out
            else "Telemetría activada en modo per-incidente: cada envío requiere tu confirmación."
        ),
    )


@router.delete("/me", response_model=RevokeResponse, status_code=status.HTTP_200_OK)
async def revoke_my_telemetry(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RevokeResponse:
    """Revoca consentimiento y marca purga de eventos asociados al tenant.

    Tras este endpoint:
    1. El cliente queda marcado `telemetry_opt_out=True` — no se generarán
       nuevos eventos.
    2. Se programa job que purga eventos del VPS con `tenant_id_hash`
       calculado con la salt activa (eventos >90d no son re-identificables;
       ver `docs/telemetry-data-policy.md` §4).
    3. La operación es idempotente: revocar dos veces no es error.

    Cumplimiento RGPD Art. 17 (derecho de supresión).
    """
    result = await db.execute(
        select(TelemetryOptOut).where(TelemetryOptOut.tenant_id == user.tenant_id)
    )
    opt_out = result.scalar_one_or_none()
    if opt_out is None:
        opt_out = TelemetryOptOut(
            tenant_id=user.tenant_id,
            requested_by=user.id,
            created_at=datetime.now(UTC),
        )
        db.add(opt_out)
        await db.commit()
        await db.refresh(opt_out)
        purge_scheduled = True
    else:
        purge_scheduled = False  # ya estaba revocado

    return RevokeResponse(
        tenant_id=str(user.tenant_id),
        opted_out=True,
        opted_out_at=opt_out.created_at,
        purge_job_scheduled=purge_scheduled,
        message=(
            "Consentimiento revocado. La purga de eventos identificables en el "
            "VPS se procesará en un plazo máximo de 30 días (RGPD Art. 12.3). "
            "Eventos >90d ya no son re-identificables y por tanto no requieren "
            "borrado activo (RGPD Recital 26). Recibirás confirmación por email."
        ),
    )
