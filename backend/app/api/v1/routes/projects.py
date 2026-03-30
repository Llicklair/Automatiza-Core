from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.projects import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectTaskCreate,
    ProjectTaskResponse,
    ProjectTaskUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Project, ProjectTask, User
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/projects", tags=["projects"])

# --- Projects ---
@router.get("", response_model=list[ProjectResponse])
@limiter.limit("30/minute")
async def list_projects(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Project).where(Project.tenant_id == current_user.tenant_id).order_by(desc(Project.created_at))
    result = await db.execute(query)
    return result.scalars().all()

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_project(
    request: Request,
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_project = Project(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return new_project

@router.patch("/{project_id}", response_model=ProjectResponse)
@limiter.limit("30/minute")
async def update_project(
    request: Request,
    project_id: UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.tenant_id == current_user.tenant_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_project(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.tenant_id == current_user.tenant_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()

# --- Project Tasks ---
@router.get("/tasks", response_model=list[ProjectTaskResponse])
@limiter.limit("30/minute")
async def list_tasks(
    request: Request,
    project_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(ProjectTask).where(ProjectTask.tenant_id == current_user.tenant_id)
    if project_id:
        query = query.where(ProjectTask.project_id == project_id)
    query = query.order_by(desc(ProjectTask.created_at))
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/tasks", response_model=ProjectTaskResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_task(
    request: Request,
    payload: ProjectTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_task = ProjectTask(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task

@router.patch("/tasks/{task_id}", response_model=ProjectTaskResponse)
@limiter.limit("30/minute")
async def update_task(
    request: Request,
    task_id: UUID,
    payload: ProjectTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProjectTask).where(
            ProjectTask.id == task_id,
            ProjectTask.tenant_id == current_user.tenant_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)
    return task

@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_task(
    request: Request,
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProjectTask).where(
            ProjectTask.id == task_id,
            ProjectTask.tenant_id == current_user.tenant_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()
