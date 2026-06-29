from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.auth import User
from app.db.models.crm import Client
from app.db.models.models import Project, ProjectTask


async def _assert_fk_in_tenant(
    db: AsyncSession,
    model: type,
    entity_id: UUID | None,
    tenant_id: UUID,
    label: str,
) -> None:
    """Reject a foreign key pointing to another tenant's row (cross-tenant IDOR).

    No-op when ``entity_id`` is None (the FK is optional). Raises LookupError when the
    referenced row does not exist within ``tenant_id`` — the same 'not found' semantics
    the rest of this service uses, so a caller cannot assign across tenants nor probe
    which IDs exist in other tenants.
    """
    if entity_id is None:
        return
    found = await db.execute(
        select(model.id).where(model.id == entity_id, model.tenant_id == tenant_id)
    )
    if found.scalar_one_or_none() is None:
        raise LookupError(f"{label} not found")


# ---- Projects ----


async def list_projects(db: AsyncSession, tenant_id: UUID) -> list[Project]:
    query = select(Project).where(Project.tenant_id == tenant_id).order_by(desc(Project.created_at))
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_project(db: AsyncSession, tenant_id: UUID, data: dict) -> Project:
    await _assert_fk_in_tenant(db, Client, data.get("client_id"), tenant_id, "Client")
    project = Project(tenant_id=tenant_id, **data)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update_project(
    db: AsyncSession, tenant_id: UUID, project_id: UUID, data: dict
) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise LookupError("Project not found")
    if "client_id" in data:
        await _assert_fk_in_tenant(db, Client, data.get("client_id"), tenant_id, "Client")
    for key, value in data.items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, tenant_id: UUID, project_id: UUID) -> None:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
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
    query = (
        select(ProjectTask)
        .where(ProjectTask.tenant_id == tenant_id)
        .options(selectinload(ProjectTask.project))
    )
    if project_id:
        query = query.where(ProjectTask.project_id == project_id)
    query = query.order_by(desc(ProjectTask.created_at))
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_task(db: AsyncSession, tenant_id: UUID, data: dict) -> ProjectTask:
    await _assert_fk_in_tenant(db, User, data.get("assignee_id"), tenant_id, "Assignee")
    await _assert_fk_in_tenant(db, Project, data.get("project_id"), tenant_id, "Project")
    task = ProjectTask(tenant_id=tenant_id, **data)
    db.add(task)
    await db.commit()
    result = await db.execute(
        select(ProjectTask)
        .where(ProjectTask.id == task.id)
        .options(selectinload(ProjectTask.project))
    )
    return result.scalar_one()


async def update_task(db: AsyncSession, tenant_id: UUID, task_id: UUID, data: dict) -> ProjectTask:
    result = await db.execute(
        select(ProjectTask).where(ProjectTask.id == task_id, ProjectTask.tenant_id == tenant_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise LookupError("Task not found")
    if "assignee_id" in data:
        await _assert_fk_in_tenant(db, User, data.get("assignee_id"), tenant_id, "Assignee")
    if "project_id" in data:
        await _assert_fk_in_tenant(db, Project, data.get("project_id"), tenant_id, "Project")
    for key, value in data.items():
        setattr(task, key, value)
    await db.commit()
    result = await db.execute(
        select(ProjectTask)
        .where(ProjectTask.id == task_id)
        .options(selectinload(ProjectTask.project))
    )
    return result.scalar_one()


async def delete_task(db: AsyncSession, tenant_id: UUID, task_id: UUID) -> None:
    result = await db.execute(
        select(ProjectTask).where(ProjectTask.id == task_id, ProjectTask.tenant_id == tenant_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise LookupError("Task not found")
    await db.delete(task)
    await db.commit()
