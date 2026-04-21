"""Rutas para Workflows & Automatizaciones — thin controller."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import workflows as schemas
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import models
from app.middleware.rate_limit import limiter
from app.services.workflow import service as svc

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflows & Automations"])


@router.get("/", response_model=list[schemas.WorkflowResponse])
@limiter.limit("30/minute")
async def list_workflows(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_workflows(current_user.tenant_id, db)


@router.get("/recent-completions")
@limiter.limit("30/minute")
async def recent_completions(
    request: Request,
    since: float = Query(default=0.0, description="Unix timestamp"),
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.recent_completions(current_user.tenant_id, since, db)


@router.post("/", response_model=schemas.WorkflowResponse, status_code=201)
@limiter.limit("30/minute")
async def create_workflow(
    request: Request,
    workflow_in: schemas.WorkflowCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.create_workflow(workflow_in, current_user.tenant_id, current_user.id, db)


@router.get("/{workflow_id}", response_model=schemas.WorkflowResponse)
@limiter.limit("30/minute")
async def get_workflow(
    request: Request,
    workflow_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wf = await svc.get_workflow(workflow_id, current_user.tenant_id, db)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    return wf


@router.patch("/{workflow_id}", response_model=schemas.WorkflowResponse)
@limiter.limit("30/minute")
async def update_workflow(
    request: Request,
    workflow_id: UUID,
    workflow_in: schemas.WorkflowUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wf = await svc.update_workflow(workflow_id, workflow_in, current_user.tenant_id, db)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    return wf


@router.delete("/{workflow_id}")
@limiter.limit("30/minute")
async def delete_workflow(
    request: Request,
    workflow_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await svc.delete_workflow(workflow_id, current_user.tenant_id, db):
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    return {"message": "Workflow eliminado correctamente"}


@router.post("/{workflow_id}/run", response_model=schemas.WorkflowExecutionResponse)
@limiter.limit("30/minute")
async def run_workflow_manually(
    request: Request,
    workflow_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.run_workflow(workflow_id, current_user.tenant_id, current_user.id, db)
    except ValueError as e:
        status = 409 if "en curso" in str(e) else 400 if "desactivado" in str(e) else 404
        raise HTTPException(status_code=status, detail=str(e))


@router.post(
    "/{workflow_id}/executions/{execution_id}/cancel",
    response_model=schemas.WorkflowExecutionResponse,
)
@limiter.limit("30/minute")
async def cancel_execution(
    request: Request,
    workflow_id: UUID,
    execution_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        execution = await svc.cancel_execution(
            execution_id, workflow_id, current_user.tenant_id, db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not execution:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    return execution


@router.post("/{workflow_id}/run-with-context", response_model=schemas.WorkflowExecutionResponse)
@limiter.limit("30/minute")
async def run_workflow_with_context(
    request: Request,
    workflow_id: UUID,
    body: dict,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    context_msg = (body.get("context") or "").strip()
    try:
        return await svc.run_workflow_with_context(
            workflow_id,
            context_msg,
            current_user.tenant_id,
            current_user.id,
            db,
        )
    except ValueError as e:
        status = 400 if "desactivado" in str(e) else 404
        raise HTTPException(status_code=status, detail=str(e))


@router.post(
    "/{workflow_id}/executions/{execution_id}/resume",
    response_model=schemas.WorkflowExecutionResponse,
)
@limiter.limit("30/minute")
async def resume_execution(
    request: Request,
    workflow_id: UUID,
    execution_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        execution = await svc.resume_execution(
            execution_id, workflow_id, current_user.tenant_id, db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al programar la reanudación: {e}")
    if not execution:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    return execution


@router.get("/{workflow_id}/executions/{execution_id}/logs")
@limiter.limit("30/minute")
async def get_execution_logs(
    request: Request,
    workflow_id: UUID,
    execution_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await svc.get_execution_logs(execution_id, workflow_id, current_user.tenant_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    return result


@router.get("/{workflow_id}/executions", response_model=list[schemas.WorkflowExecutionResponse])
@limiter.limit("30/minute")
async def get_workflow_executions(
    request: Request,
    workflow_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_executions(workflow_id, current_user.tenant_id, db)


@router.post("/parse-nl", response_model=schemas.WorkflowParseResponse)
@limiter.limit("30/minute")
async def parse_natural_language_workflow(
    request: Request,
    body: schemas.WorkflowParseRequest,
    current_user: models.User = Depends(get_current_user),
):
    try:
        payload = await svc.parse_natural_language(body.text)
        return schemas.WorkflowParseResponse(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo parsear la regla: {str(e)}")


@router.post("/fire-event")
@limiter.limit("30/minute")
async def fire_workflow_event(
    request: Request,
    body: dict[str, Any],
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event_name = body.get("event", "")
    context = body.get("context", {})
    triggered = await svc.fire_event(
        event_name,
        context,
        current_user.tenant_id,
        current_user.id,
        db,
    )
    return {"triggered_workflows": triggered, "event": event_name, "count": len(triggered)}
