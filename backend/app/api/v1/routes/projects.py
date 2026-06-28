"""Rutas Projects — thin controller para proyectos y tareas de proyecto."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.projects import (
    ProjectCreate,
    ProjectResponse,
    ProjectTaskCreate,
    ProjectTaskResponse,
    ProjectTaskUpdate,
    ProjectUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services import project_service as svc

router = APIRouter(prefix="/projects", tags=["projects"])


# --- Projects ---
@router.get("", response_model=list[ProjectResponse])
@limiter.limit("30/minute")
async def list_projects(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_projects(db, current_user.tenant_id)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_project(
    request: Request,
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.create_project(db, current_user.tenant_id, payload.model_dump())


@router.patch("/{project_id}", response_model=ProjectResponse)
@limiter.limit("30/minute")
async def update_project(
    request: Request,
    project_id: UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_project(
            db, current_user.tenant_id, project_id, payload.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_project(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_project(db, current_user.tenant_id, project_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# --- Project Tasks ---
@router.get("/tasks", response_model=list[ProjectTaskResponse])
@limiter.limit("30/minute")
async def list_tasks(
    request: Request,
    project_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_tasks(db, current_user.tenant_id, project_id)


@router.post("/tasks", response_model=ProjectTaskResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_task(
    request: Request,
    payload: ProjectTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.create_task(db, current_user.tenant_id, payload.model_dump())


@router.patch("/tasks/{task_id}", response_model=ProjectTaskResponse)
@limiter.limit("30/minute")
async def update_task(
    request: Request,
    task_id: UUID,
    payload: ProjectTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_task(
            db, current_user.tenant_id, task_id, payload.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_task(
    request: Request,
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_task(db, current_user.tenant_id, task_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
