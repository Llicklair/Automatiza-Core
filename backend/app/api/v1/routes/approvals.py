"""Rutas de aprobaciones humanas pendientes."""
import logging
from datetime import UTC, datetime
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import PendingApproval, Task, User, WorkflowExecution
from app.api.v1.schemas.tasks import ApprovalDecision, PendingApprovalOut
from app.services.audit import log_action

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[PendingApprovalOut])
async def list_pending_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista aprobaciones pendientes del tenant, ordenadas por urgencia (expiración próxima)."""
    result = await db.execute(
        select(PendingApproval)
        .where(
            PendingApproval.tenant_id == current_user.tenant_id,
            PendingApproval.status == "pending",
        )
        .order_by(PendingApproval.expires_at)
    )
    return result.scalars().all()


@router.post("/{approval_id}/decide", response_model=PendingApprovalOut)
async def decide_approval(
    approval_id: UUID,
    decision: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PendingApproval).where(
            PendingApproval.id == approval_id,
            PendingApproval.tenant_id == current_user.tenant_id,
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Aprobación no encontrada")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Ya fue resuelta: {approval.status}")

    now = datetime.now(UTC)
    if approval.expires_at < now:
        approval.status = "expired"
        await db.commit()
        raise HTTPException(status_code=410, detail="La aprobación ha expirado")

    approval.approved_by = current_user.id
    approval.approved_at = now
    approval.status = "approved" if decision.approved else "rejected"
    if not decision.approved:
        approval.rejection_reason = decision.rejection_reason

    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        agent_name="human",
        action_type="approval_decision",
        status=approval.status,
        task_id=approval.task_id,
        input_data={"decision": decision.model_dump()},
        output_data={"approval_id": str(approval_id), "risk_level": approval.risk_level},
    )

    await db.commit()
    await db.refresh(approval)

    # Notificar al orquestador del resultado (resumir tarea si estaba esperando)
    if decision.approved:
        await _resume_after_approval(approval, db)

    return approval


@router.delete("/cleanup", status_code=200)
async def cleanup_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina TODAS las aprobaciones. Las pendientes se rechazan y sus tareas/workflows se cancelan."""
    from sqlalchemy import delete as sql_delete, update as sql_update

    # Obtener aprobaciones pendientes para cancelar sus tareas/workflows
    pending_result = await db.execute(
        select(PendingApproval).where(
            PendingApproval.tenant_id == current_user.tenant_id,
            PendingApproval.status == "pending",
        )
    )
    pending = pending_result.scalars().all()

    if pending:
        # Cancelar las tareas asociadas a aprobaciones pendientes
        pending_task_ids = [a.task_id for a in pending if a.task_id]
        if pending_task_ids:
            await db.execute(
                sql_update(Task)
                .where(Task.id.in_(pending_task_ids), Task.status.notin_(["done", "failed", "cancelled"]))
                .values(status="cancelled")
            )
            # Revocar tareas activas
            try:
                from app.services.task_dispatch import cancel_task
                for tid in pending_task_ids:
                    await cancel_task(str(tid))
            except Exception as e:
                logger.warning("Error al revocar tareas pendientes durante cancelación masiva: %s", e)

        # Cancelar workflow executions asociadas
        pending_exec_ids = [a.execution_id for a in pending if a.execution_id]
        if pending_exec_ids:
            await db.execute(
                sql_update(WorkflowExecution)
                .where(WorkflowExecution.id.in_(pending_exec_ids), WorkflowExecution.status.in_(["pending", "running"]))
                .values(status="cancelled")
            )

    # Eliminar TODAS las aprobaciones del tenant
    result = await db.execute(
        sql_delete(PendingApproval)
        .where(PendingApproval.tenant_id == current_user.tenant_id)
        .returning(PendingApproval.id)
    )
    deleted = len(result.fetchall())
    await db.commit()
    return {"deleted": deleted}


async def _resume_after_approval(approval: PendingApproval, db: AsyncSession):
    """Reanuda el flujo tras una aprobación — NodeEngine o LangGraph."""
    try:
        # Si tiene execution_id, es un approval gate del motor de nodos
        if approval.execution_id:
            payload = approval.action_payload or {}
            node_id = payload.get("node_id")
            if node_id:
                from app.services.task_dispatch import dispatch_resume_node_engine
                await dispatch_resume_node_engine(str(approval.execution_id), node_id)
                return

        # Fallback: orquestador clásico
        from app.services.task_dispatch import dispatch_resume_orchestrator
        await dispatch_resume_orchestrator(str(approval.task_id))
    except Exception as e:
        logger.warning("Error al reanudar flujo tras aprobación (task_id=%s): %s", approval.task_id, e)
