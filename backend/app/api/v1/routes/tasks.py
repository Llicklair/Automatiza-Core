"""Rutas CRUD de tareas del orquestador."""
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import AuditLog, PendingApproval, Task, TenantDocument, User, WorkflowExecution
from app.api.v1.schemas.tasks import AuditLogOut, TaskCreate, TaskOut

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = Task(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        domain=payload.domain,
        user_intent=payload.user_intent,
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Encolar ejecución en Celery (asíncrona) pasando el task_id
    background_tasks.add_task(_enqueue_task, str(task.id))

    return task


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    skip: int = 0,
    limit: int = Query(default=50, le=100),
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Task)
        .where(Task.tenant_id == current_user.tenant_id)
        .order_by(desc(Task.created_at))
        .offset(skip)
        .limit(limit)
    )
    if status_filter:
        query = query.where(Task.status == status_filter)

    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina TODAS las tareas del tenant. Las activas se cancelan primero (Celery revoke)."""
    from sqlalchemy import delete as sql_delete, update as sql_update

    # Obtener TODAS las tareas del tenant
    ids_result = await db.execute(
        select(Task.id, Task.status).where(Task.tenant_id == current_user.tenant_id)
    )
    rows = ids_result.fetchall()
    if not rows:
        return {"deleted": 0, "cancelled": 0}

    task_ids = [row[0] for row in rows]
    active_ids = [row[0] for row in rows if row[1] in ("pending", "planning", "executing", "awaiting_approval")]

    # Cancelar tareas activas en Celery
    cancelled = 0
    if active_ids:
        try:
            from app.workers.celery_app import celery_app
            for tid in active_ids:
                celery_app.control.revoke(str(tid), terminate=True, signal="SIGKILL")
        except Exception as e:
            print(f"Error al revocar tareas en Celery: {e}")
        # Marcar como canceladas antes de borrar (para WorkflowExecutions asociadas)
        await db.execute(
            sql_update(Task)
            .where(Task.id.in_(active_ids))
            .values(status="cancelled")
        )
        cancelled = len(active_ids)

    # Cancelar workflow executions asociadas que estén activas
    await db.execute(
        sql_update(WorkflowExecution)
        .where(
            WorkflowExecution.task_id.in_(task_ids),
            WorkflowExecution.status.in_(["pending", "running"]),
        )
        .values(status="cancelled")
    )

    # Eliminar registros que referencian tasks (FK constraints)
    await db.execute(sql_delete(AuditLog).where(AuditLog.task_id.in_(task_ids)))
    await db.execute(sql_delete(PendingApproval).where(PendingApproval.task_id.in_(task_ids)))
    # Nullable FKs: poner a NULL en vez de borrar
    await db.execute(sql_update(TenantDocument).where(TenantDocument.task_id.in_(task_ids)).values(task_id=None))
    await db.execute(sql_update(WorkflowExecution).where(WorkflowExecution.task_id.in_(task_ids)).values(task_id=None))

    # Borrar las tareas
    await db.execute(sql_delete(Task).where(Task.id.in_(task_ids)))

    await db.commit()
    return {"deleted": len(task_ids), "cancelled": cancelled}


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.tenant_id == current_user.tenant_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.tenant_id == current_user.tenant_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if task.status in ("done", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Tarea en estado '{task.status}' no se puede cancelar")

    task.status = "cancelled"
    await db.commit()

    # Cancelar la tarea en Celery si está en ejecución
    try:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(str(task_id), terminate=True, signal='SIGKILL')
    except Exception as e:
        print(f"Error al revocar la tarea en Celery: {e}")


@router.get("/{task_id}/audit", response_model=list[AuditLogOut])
async def get_task_audit(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el log completo de auditoría de una tarea."""
    # Verificar que la tarea pertenece al tenant
    task_result = await db.execute(
        select(Task).where(Task.id == task_id, Task.tenant_id == current_user.tenant_id)
    )
    if not task_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.task_id == task_id)
        .order_by(AuditLog.executed_at)
    )
    entries = result.scalars().all()

    # Ocultar prompts LLM a usuarios no admin
    if current_user.role != "admin":
        for e in entries:
            e.llm_prompt = None
            e.llm_response = None

    return entries


async def _enqueue_task(task_id: str):
    """Encola la tarea en Celery forzando que el ID de la BD sea el ID de Celery."""
    try:
        from app.workers.celery_app import run_orchestrator
        # Usar apply_async para asginar manualmente el task_id de Celery
        run_orchestrator.apply_async(args=[task_id], task_id=task_id)
    except Exception as e:
        print(f"Error encolando tarea: {e}")
