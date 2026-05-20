"""Servicio de aprobaciones — lógica de negocio pura (sin HTTPException)."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import as_aware
from app.db.models.models import PendingApproval, Task, WorkflowExecution
from app.services.audit import log_action

logger = logging.getLogger(__name__)


async def list_pending(db: AsyncSession, tenant_id: UUID) -> list[PendingApproval]:
    """Lista aprobaciones pendientes del tenant, ordenadas por expiración."""
    result = await db.execute(
        select(PendingApproval)
        .where(
            PendingApproval.tenant_id == tenant_id,
            PendingApproval.status == "pending",
        )
        .order_by(PendingApproval.expires_at)
    )
    return list(result.scalars().all())


async def decide(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    approval_id: UUID,
    approved: bool,
    rejection_reason: str | None = None,
) -> PendingApproval:
    """Procesa la decisión de aprobación. Raises ValueError/LookupError."""
    result = await db.execute(
        select(PendingApproval).where(
            PendingApproval.id == approval_id,
            PendingApproval.tenant_id == tenant_id,
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise LookupError("Aprobación no encontrada")
    if approval.status != "pending":
        raise ValueError(f"Ya fue resuelta: {approval.status}")

    now = datetime.now(UTC)
    expires_at = as_aware(approval.expires_at)
    if expires_at is not None and expires_at < now:
        approval.status = "expired"
        await db.commit()
        raise TimeoutError("La aprobación ha expirado")

    approval.approved_by = user_id
    approval.approved_at = now
    approval.status = "approved" if approved else "rejected"
    if not approved:
        approval.rejection_reason = rejection_reason

    await log_action(
        db,
        tenant_id=tenant_id,
        agent_name="human",
        action_type="approval_decision",
        status=approval.status,
        task_id=approval.task_id,
        input_data={"decision": {"approved": approved, "rejection_reason": rejection_reason}},
        output_data={"approval_id": str(approval_id), "risk_level": approval.risk_level},
    )

    await db.commit()
    await db.refresh(approval)

    if approved:
        await _resume_after_approval(approval, db)

    return approval


async def cleanup_all(db: AsyncSession, tenant_id: UUID) -> int:
    """Elimina TODAS las aprobaciones. Las pendientes se rechazan y sus tareas/workflows se cancelan."""
    pending_result = await db.execute(
        select(PendingApproval).where(
            PendingApproval.tenant_id == tenant_id,
            PendingApproval.status == "pending",
        )
    )
    pending = pending_result.scalars().all()

    if pending:
        pending_task_ids = [a.task_id for a in pending if a.task_id]
        if pending_task_ids:
            await db.execute(
                sql_update(Task)
                .where(
                    Task.id.in_(pending_task_ids),
                    Task.status.notin_(["done", "failed", "cancelled"]),
                )
                .values(status="cancelled")
            )
            try:
                from app.services.workflow.task_dispatch import cancel_task

                for tid in pending_task_ids:
                    await cancel_task(str(tid))
            except Exception as e:
                logger.warning(
                    "Error al revocar tareas pendientes durante cancelación masiva: %s", e
                )

        pending_exec_ids = [a.execution_id for a in pending if a.execution_id]
        if pending_exec_ids:
            await db.execute(
                sql_update(WorkflowExecution)
                .where(
                    WorkflowExecution.id.in_(pending_exec_ids),
                    WorkflowExecution.status.in_(["pending", "running"]),
                )
                .values(status="cancelled")
            )

    result = await db.execute(
        sql_delete(PendingApproval)
        .where(PendingApproval.tenant_id == tenant_id)
        .returning(PendingApproval.id)
    )
    deleted = len(result.fetchall())
    await db.commit()
    return deleted


async def _resume_after_approval(approval: PendingApproval, db: AsyncSession) -> None:
    """Reanuda el flujo tras una aprobación — NodeEngine o LangGraph."""
    try:
        # Fase 3 (RLS): el PendingApproval ya está scoped por tenant — lo propagamos
        # al dispatcher para que el worker fije el ContextVar antes del bootstrap.
        tenant_id = str(approval.tenant_id) if approval.tenant_id else None

        if approval.execution_id:
            payload = approval.action_payload or {}
            node_id = payload.get("node_id")
            if node_id:
                from app.services.workflow.task_dispatch import dispatch_resume_node_engine

                await dispatch_resume_node_engine(
                    str(approval.execution_id), node_id, tenant_id=tenant_id
                )
                return

        from app.services.workflow.task_dispatch import dispatch_resume_orchestrator

        await dispatch_resume_orchestrator(str(approval.task_id), tenant_id=tenant_id)
    except Exception as e:
        logger.warning(
            "Error al reanudar flujo tras aprobación (task_id=%s): %s", approval.task_id, e
        )
