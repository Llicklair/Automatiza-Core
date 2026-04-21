"""
Scheduler-layer DB helpers for workflow execution.

These functions encapsulate all raw DB access that APScheduler tasks need
so the worker (tasks_scheduler.py) stays free of sqlalchemy calls.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Task, Workflow, WorkflowExecution

logger = logging.getLogger(__name__)


async def get_active_scheduled_workflows(db: AsyncSession) -> list[Workflow]:
    """Return all active schedule_based workflows."""
    result = await db.execute(
        select(Workflow).where(
            Workflow.is_active.is_(True),
            Workflow.trigger_type == "schedule_based",
        )
    )
    return list(result.scalars().all())


async def has_active_execution(db: AsyncSession, workflow_id) -> bool:
    """Return True if the workflow already has a running/pending execution."""
    result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.workflow_id == workflow_id,
            WorkflowExecution.status.in_(["running", "pending"]),
        )
    )
    return result.scalars().first() is not None


async def get_last_execution(db: AsyncSession, workflow_id) -> WorkflowExecution | None:
    """Return the most recent execution for a workflow, or None."""
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.workflow_id == workflow_id)
        .order_by(WorkflowExecution.started_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def create_execution(
    db: AsyncSession, workflow: Workflow, trigger_payload: dict
) -> WorkflowExecution:
    """Insert a new WorkflowExecution and flush (no commit)."""
    execution = WorkflowExecution(
        workflow_id=workflow.id,
        tenant_id=workflow.tenant_id,
        status="running",
        trigger_payload=trigger_payload,
    )
    db.add(execution)
    await db.flush()
    return execution


async def create_task_for_execution(
    db: AsyncSession,
    workflow: Workflow,
    execution: WorkflowExecution,
    domain: str,
    user_intent: str,
    initial_status: str,
    meta: dict,
) -> Task:
    """Insert a Task linked to an execution and flush (no commit)."""
    task = Task(
        tenant_id=workflow.tenant_id,
        created_by=None,
        domain=domain,
        user_intent=user_intent,
        status=initial_status,
        additional_metadata=meta,
    )
    db.add(task)
    await db.flush()
    execution.task_id = task.id
    await db.flush()
    return task


async def get_stuck_executions(db: AsyncSession, cutoff: datetime) -> list[WorkflowExecution]:
    """Return executions stuck in 'running' state older than *cutoff*."""
    result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.status == "running",
            WorkflowExecution.started_at < cutoff,
        )
    )
    return list(result.scalars().all())


async def mark_executions_failed(
    db: AsyncSession, executions: list[WorkflowExecution], note: str
) -> None:
    """Mark a list of executions as failed (no commit)."""
    now = datetime.now(UTC)
    for ex in executions:
        ex.status = "failed"
        ex.completed_at = now
        ex.result_log = (ex.result_log or "") + f" {note}"
