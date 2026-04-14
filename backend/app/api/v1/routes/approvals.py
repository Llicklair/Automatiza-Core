"""Rutas de aprobaciones humanas pendientes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.approvals import ApprovalDecision, PendingApprovalOut
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.workflow import approval as svc

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[PendingApprovalOut])
@limiter.limit("30/minute")
async def list_pending_approvals(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista aprobaciones pendientes del tenant, ordenadas por urgencia (expiración próxima)."""
    return await svc.list_pending(db, current_user.tenant_id)


@router.post("/{approval_id}/decide", response_model=PendingApprovalOut)
@limiter.limit("30/minute")
async def decide_approval(
    request: Request,
    approval_id: UUID,
    decision: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.decide(
            db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            approval_id=approval_id,
            approved=decision.approved,
            rejection_reason=decision.rejection_reason,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=410, detail=str(e))


@router.delete("/cleanup", status_code=200)
@limiter.limit("30/minute")
async def cleanup_approvals(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina TODAS las aprobaciones. Las pendientes se rechazan y sus tareas/workflows se cancelan."""
    deleted = await svc.cleanup_all(db, current_user.tenant_id)
    return {"deleted": deleted}
