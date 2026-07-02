"""Servicio de dominio para Workflows & Automatizaciones.

CRUD de workflows/executions y queries. La logica de ejecucion, NLP y grafos
UI esta en sub-modulos (_execution, _nlp, _ui_graph) y se re-exporta aqui
para compatibilidad.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models import models

# Re-exports desde sub-modulos para backward compatibility
from app.services.workflow._execution import (  # noqa: F401
    cancel_execution,
    execute_deterministic_steps,
    resume_execution,
    run_workflow,
    run_workflow_with_context,
)
from app.services.workflow._nlp import (  # noqa: F401
    fire_event,
    parse_natural_language,
)
from app.services.workflow._ui_graph import (  # noqa: F401
    generate_preview_nodes,
    plan_to_ui_graph,
)

logger = logging.getLogger(__name__)


# â”€â”€ CRUD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def list_workflows(tenant_id, db: AsyncSession) -> list[models.Workflow]:
    result = await db.execute(select(models.Workflow).where(models.Workflow.tenant_id == tenant_id))
    return list(result.scalars().all())


async def create_workflow(workflow_in, tenant_id, user_id, db: AsyncSession) -> models.Workflow:
    db_workflow = models.Workflow(
        tenant_id=tenant_id,
        created_by=user_id,
        name=workflow_in.name,
        description=workflow_in.description,
        is_active=workflow_in.is_active,
        trigger_type=workflow_in.trigger_type,
        trigger_config=workflow_in.trigger_config,
        action_type=workflow_in.action_type,
        action_config=workflow_in.action_config,
        execution_mode=workflow_in.execution_mode,
        compiled_steps=workflow_in.compiled_steps if hasattr(workflow_in, "compiled_steps") else None,
        ui_nodes=workflow_in.ui_nodes or [],
        ui_edges=workflow_in.ui_edges or [],
    )
    db.add(db_workflow)
    await db.commit()
    await db.refresh(db_workflow)
    return db_workflow


async def get_workflow(workflow_id: UUID, tenant_id, db: AsyncSession) -> models.Workflow | None:
    result = await db.execute(
        select(models.Workflow).where(models.Workflow.id == workflow_id, models.Workflow.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def update_workflow(
    workflow_id: UUID,
    workflow_in,
    tenant_id,
    db: AsyncSession,
) -> models.Workflow | None:
    wf = await get_workflow(workflow_id, tenant_id, db)
    if not wf:
        return None
    update_data = workflow_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(wf, key, value)
    await db.commit()
    await db.refresh(wf)
    return wf


async def delete_workflow(workflow_id: UUID, tenant_id, db: AsyncSession) -> bool:
    wf = await get_workflow(workflow_id, tenant_id, db)
    if not wf:
        return False
    await db.delete(wf)
    await db.commit()
    return True


# â”€â”€ Recent completions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def recent_completions(tenant_id, since: float, db: AsyncSession) -> list[dict]:
    since_dt = datetime.fromtimestamp(since, tz=UTC) if since > 0 else datetime.now(UTC)
    stmt = (
        select(
            models.WorkflowExecution.id,
            models.WorkflowExecution.status,
            models.WorkflowExecution.completed_at,
            models.Workflow.name,
        )
        .join(models.Workflow, models.WorkflowExecution.workflow_id == models.Workflow.id)
        .where(
            models.WorkflowExecution.tenant_id == tenant_id,
            models.WorkflowExecution.status.in_(["completed", "success", "failed"]),
            models.WorkflowExecution.completed_at >= since_dt,
        )
        .order_by(models.WorkflowExecution.completed_at.desc())
        .limit(5)
    )
    result = await db.execute(stmt)
    rows = result.fetchall()
    return [
        {
            "id": str(r[0]),
            "status": r[1],
            "completed_at": r[2].isoformat() if r[2] else None,
            "workflow_name": r[3],
        }
        for r in rows
    ]


# â”€â”€ Execution queries â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def get_execution(
    execution_id: UUID,
    workflow_id: UUID,
    tenant_id,
    db: AsyncSession,
) -> models.WorkflowExecution | None:
    result = await db.execute(
        select(models.WorkflowExecution).where(
            models.WorkflowExecution.id == execution_id,
            models.WorkflowExecution.workflow_id == workflow_id,
            models.WorkflowExecution.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def list_executions(
    workflow_id: UUID,
    tenant_id,
    db: AsyncSession,
) -> list[models.WorkflowExecution]:
    result = await db.execute(
        select(models.WorkflowExecution)
        .where(
            models.WorkflowExecution.workflow_id == workflow_id,
            models.WorkflowExecution.tenant_id == tenant_id,
        )
        .order_by(models.WorkflowExecution.started_at.desc())
        .limit(20)
    )
    return list(result.scalars().all())


async def get_execution_logs(
    execution_id: UUID,
    workflow_id: UUID,
    tenant_id,
    db: AsyncSession,
) -> dict:
    execution = await get_execution(execution_id, workflow_id, tenant_id, db)
    if not execution:
        return None

    lines: list[str] = []
    if execution.task_id:
        try:
            from app.services.exec_log_store import get_all

            stored_lines = get_all(str(execution.task_id))
            if stored_lines:
                lines = stored_lines
        except Exception:
            logger.debug("exec_log_store unavailable, using result_log fallback", exc_info=True)

    if not lines and execution.result_log:
        lines = [execution.result_log]

    return {"lines": lines, "status": execution.status}
