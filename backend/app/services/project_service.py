from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Project, ProjectTask

# ---- Projects ----


async def list_projects(db: AsyncSession, tenant_id: UUID) -> list[Project]:
    query = (
        select(Project)
        .where(Project.tenant_id == tenant_id)
        .order_by(desc(Project.created_at))
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_project(
    db: AsyncSession, tenant_id: UUID, data: dict
) -> Project:
    project = Project(tenant_id=tenant_id, **data)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update_project(
    db: AsyncSession, tenant_id: UUID, project_id: UUID, data: dict
) -> Project:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id, Project.tenant_id == tenant_id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise LookupError("Project not found")
    for key, value in data.items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(
    db: AsyncSession, tenant_id: UUID, project_id: UUID
) -> None:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id, Project.tenant_id == tenant_id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise LookupError("Project not found")
    await db.delete(project)
    await db.commit()


# ---- Project Tasks ----


async def list_tasks(
    db: AsyncSession,
    tenant_id: UUID,
    project_id: UUID | None = None,
) -> list[ProjectTask]:
    query = select(ProjectTask).where(ProjectTask.tenant_id == tenant_id)
    if project_id:
        query = query.where(ProjectTask.project_id == project_id)
    query = query.order_by(desc(ProjectTask.created_at))
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_task(
    db: AsyncSession, tenant_id: UUID, data: dict
) -> ProjectTask:
    task = ProjectTask(tenant_id=tenant_id, **data)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(
    db: AsyncSession, tenant_id: UUID, task_id: UUID, data: dict
) -> ProjectTask:
    result = await db.execute(
        select(ProjectTask).where(
            ProjectTask.id == task_id, ProjectTask.tenant_id == tenant_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise LookupError("Task not found")
    for key, value in data.items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(
    db: AsyncSession, tenant_id: UUID, task_id: UUID
) -> None:
    result = await db.execute(
        select(ProjectTask).where(
            ProjectTask.id == task_id, ProjectTask.tenant_id == tenant_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise LookupError("Task not found")
    await db.delete(task)
    await db.commit()
