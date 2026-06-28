"""Rutas CRUD de tareas del orquestador."""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.tasks import AuditLogOut, TaskCreate, TaskOut
from app.core.dependencies import get_current_user, require_role
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.workflow import task as svc
from app.services.workflow.task_event_hub import task_event_hub

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
    limit: int = Query(default=50, le=200),
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
    current_user: User = Depends(require_role("admin")),
):
    """Oculta TODAS las tareas del tenant via soft-delete (is_deleted=True).

    Las activas se cancelan primero. Los registros audit_log y
    agent_execution_trace asociados quedan intactos (cumplimiento WORM).
    Solo admin: operación destructiva sobre la vista del workflow."""
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
        raise HTTPException(status_code=404, detail=str(e)) from e


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
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{task_id}/cost")
async def get_task_cost(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """UI.COST — agregado de tokens + EUR estimado para una task.

    Diseñado para el modal post-abort: el frontend lo invoca tras stop
    para mostrar "Has consumido N tokens (≈ 0,XX€)".
    """
    from app.services.ai.task_cost import summarize_task_cost

    result = await summarize_task_cost(
        db, tenant_id=current_user.tenant_id, task_id=task_id,
    )
    if result["task_status"] is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return result


@router.get("/{task_id}/stream")
async def stream_task_events(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE stream de eventos de progreso de una tarea (UI.AGT).

    Verifica ownership por tenant antes de abrir el stream. Cada evento se
    envía como `data: <json>\\n\\n` siguiendo la spec EventSource. El stream
    se cierra automáticamente cuando la tarea entra en estado terminal
    (completed / failed / cancelled) o por timeout de 10 min.

    El frontend consume con `fetch()` + `ReadableStream` (no EventSource —
    permite enviar el JWT en `Authorization` header).
    """
    # Ownership check: 404 si la tarea no pertenece al tenant.
    try:
        await svc.get_task(db, task_id=task_id, tenant_id=current_user.tenant_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    async def _event_generator():
        # Comment inicial para forzar flush de cabeceras en proxies (NGINX).
        yield ": stream-open\n\n"
        async for event in task_event_hub.stream(str(task_id), timeout_seconds=600.0):
            payload = json.dumps(event, default=str)
            yield f"data: {payload}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # NGINX: deshabilita buffering
            "Connection": "keep-alive",
        },
    )


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
        raise HTTPException(status_code=404, detail=str(e)) from e
