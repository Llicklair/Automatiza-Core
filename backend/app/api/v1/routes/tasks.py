"""Rutas CRUD de tareas del orquestador."""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.tasks import AuditLogOut, TaskCreate, TaskOut
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.workflow import task as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_task(
    request: Request,
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await svc.create_task(
        db,
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        domain=payload.domain,
        user_intent=payload.user_intent,
        additional_metadata=payload.additional_metadata,
        parent_task_id=payload.parent_task_id,
    )
    background_tasks.add_task(svc._enqueue_task, str(task.id))
    return task


@router.get("", response_model=list[TaskOut])
@limiter.limit("60/minute")
async def list_tasks(
    request: Request,
    skip: int = 0,
    limit: int = Query(default=50, le=100),
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_tasks(
        db,
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
    )


@router.delete("/cleanup", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def cleanup_tasks(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina TODAS las tareas del tenant. Las activas se cancelan primero."""
    return await svc.cleanup_tasks(db, tenant_id=current_user.tenant_id)


@router.get("/{task_id}", response_model=TaskOut)
@limiter.limit("60/minute")
async def get_task(
    request: Request,
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.get_task(db, task_id=task_id, tenant_id=current_user.tenant_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def cancel_task(
    request: Request,
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.cancel_task(db, task_id=task_id, tenant_id=current_user.tenant_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}/audit", response_model=list[AuditLogOut])
@limiter.limit("60/minute")
async def get_task_audit(
    request: Request,
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el log completo de auditoría de una tarea."""
    try:
        return await svc.get_task_audit(
            db,
            task_id=task_id,
            tenant_id=current_user.tenant_id,
            is_admin=current_user.role == "admin",
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
