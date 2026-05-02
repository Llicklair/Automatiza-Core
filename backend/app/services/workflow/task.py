"""Business logic for task management."""

import logging
from uuid import UUID

from sqlalchemy import delete as sql_delete
from sqlalchemy import desc, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import (
    AuditLog,
    PendingApproval,
    Task,
    TenantDocument,
    WorkflowExecution,
)

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("pending", "planning", "executing", "awaiting_approval")
TERMINAL_STATUSES = ("done", "failed", "cancelled")


# ── helpers ──────────────────────────────────────────────────────────────────


async def _build_conversation_history(
    db: AsyncSession, parent_task_id: UUID, tenant_id: UUID, max_turns: int = 10
) -> list[dict]:
    """Walk the parent-task chain to build a conversation history."""
    history: list[dict] = []
    current_id = parent_task_id

    for _ in range(max_turns):
        result = await db.execute(
            select(Task).where(Task.id == current_id, Task.tenant_id == tenant_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            break

        assistant_msg = ""
        if task.agent_results:
            for r in task.agent_results if isinstance(task.agent_results, list) else []:
                output = r.get("output", {})
                if output.get("response"):
                    assistant_msg = output["response"]
                    break

        history.insert(0, {"role": "user", "content": task.user_intent or ""})
        if assistant_msg:
            history.insert(1, {"role": "assistant", "content": assistant_msg})

        meta = task.additional_metadata or {}
        parent = meta.get("parent_task_id")
        if not parent:
            break
        current_id = UUID(parent)

    return history


async def _enqueue_task(task_id: str) -> None:
    """Dispatch the task to the orchestrator runner."""
    try:
        from app.services.workflow.task_dispatch import dispatch_orchestrator

        await dispatch_orchestrator(task_id)
    except Exception as e:
        logger.error("Error encolando tarea: %s", e)


# ── public API ───────────────────────────────────────────────────────────────


async def create_task(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    created_by: UUID,
    domain: str,
    user_intent: str,
    additional_metadata: dict | None = None,
    parent_task_id: str | None = None,
) -> Task:
    metadata = additional_metadata or {}

    if parent_task_id:
        conversation_history = await _build_conversation_history(
            db, UUID(parent_task_id), tenant_id
        )
        metadata["parent_task_id"] = parent_task_id
        metadata["conversation_history"] = conversation_history

    task = Task(
        tenant_id=tenant_id,
        created_by=created_by,
        domain=domain,
        user_intent=user_intent,
        status="pending",
        additional_metadata=metadata,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def list_tasks(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
) -> list[Task]:
    query = (
        select(Task)
        .where(Task.tenant_id == tenant_id)
        .order_by(desc(Task.created_at))
        .offset(skip)
        .limit(limit)
    )
    if status_filter:
        query = query.where(Task.status == status_filter)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_task(db: AsyncSession, *, task_id: UUID, tenant_id: UUID) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id, Task.tenant_id == tenant_id))
    task = result.scalar_one_or_none()
    if not task:
        raise LookupError("Tarea no encontrada")
    return task


async def cancel_task(db: AsyncSession, *, task_id: UUID, tenant_id: UUID) -> None:
    task = await get_task(db, task_id=task_id, tenant_id=tenant_id)

    if task.status in TERMINAL_STATUSES:
        raise ValueError(f"Tarea en estado '{task.status}' no se puede cancelar")

    task.status = "cancelled"
    await db.commit()

    try:
        from app.services.workflow.task_dispatch import cancel_task as cancel_task_dispatch

        await cancel_task_dispatch(str(task_id))
    except Exception as e:
        logger.error("Error al revocar la tarea: %s", e)


async def cleanup_tasks(db: AsyncSession, *, tenant_id: UUID) -> dict:
    ids_result = await db.execute(select(Task.id, Task.status).where(Task.tenant_id == tenant_id))
    rows = ids_result.fetchall()
    if not rows:
        return {"deleted": 0, "cancelled": 0}

    task_ids = [row[0] for row in rows]
    active_ids = [row[0] for row in rows if row[1] in ACTIVE_STATUSES]

    cancelled = 0
    if active_ids:
        try:
            from app.services.workflow.task_dispatch import cancel_task as cancel_task_dispatch

            for tid in active_ids:
                await cancel_task_dispatch(str(tid))
        except Exception as e:
            logger.error("Error al revocar tareas: %s", e)
        await db.execute(sql_update(Task).where(Task.id.in_(active_ids)).values(status="cancelled"))
        cancelled = len(active_ids)

    await db.execute(
        sql_update(WorkflowExecution)
        .where(
            WorkflowExecution.task_id.in_(task_ids),
            WorkflowExecution.status.in_(["pending", "running"]),
        )
        .values(status="cancelled")
    )

    await db.execute(
        sql_delete(AuditLog).where(
            AuditLog.task_id.in_(task_ids),
            AuditLog.tenant_id == tenant_id,
        )
    )
    await db.execute(sql_delete(PendingApproval).where(PendingApproval.task_id.in_(task_ids)))
    await db.execute(
        sql_update(TenantDocument).where(TenantDocument.task_id.in_(task_ids)).values(task_id=None)
    )
    await db.execute(
        sql_update(WorkflowExecution)
        .where(WorkflowExecution.task_id.in_(task_ids))
        .values(task_id=None)
    )

    await db.execute(sql_delete(Task).where(Task.id.in_(task_ids)))
    await db.commit()

    return {"deleted": len(task_ids), "cancelled": cancelled}


async def get_task_audit(
    db: AsyncSession, *, task_id: UUID, tenant_id: UUID, is_admin: bool
) -> list[AuditLog]:
    # Verify task belongs to tenant
    await get_task(db, task_id=task_id, tenant_id=tenant_id)

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.task_id == task_id, AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.executed_at)
    )
    entries = list(result.scalars().all())

    if not is_admin:
        for e in entries:
            e.llm_prompt = None
            e.llm_response = None

    return entries
