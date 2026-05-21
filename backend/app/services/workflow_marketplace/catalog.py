"""Catálogo de plantillas + instalación en el tenant (F3.10)."""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workflow_template import WorkflowTemplate
from app.db.models.workflows import Workflow


def _template_to_dict(t: WorkflowTemplate) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "slug": t.slug,
        "name": t.name,
        "description": t.description,
        "category": t.category,
        "author": t.author,
        "trigger_type": t.trigger_type,
        "trigger_config": t.trigger_config or {},
        "action_type": t.action_type,
        "action_config": t.action_config or {},
        "execution_mode": t.execution_mode,
        "compiled_steps": t.compiled_steps,
        "tags": t.tags or [],
        "is_official": bool(t.is_official),
        "downloads_count": int(t.downloads_count or 0),
    }


async def list_templates(
    db: AsyncSession, *, category: str | None = None
) -> list[dict[str, Any]]:
    stmt = sa.select(WorkflowTemplate).order_by(
        WorkflowTemplate.is_official.desc(),
        WorkflowTemplate.downloads_count.desc(),
        WorkflowTemplate.name.asc(),
    )
    if category:
        stmt = stmt.where(WorkflowTemplate.category == category)
    res = await db.execute(stmt)
    return [_template_to_dict(t) for t in res.scalars().all()]


async def get_template(db: AsyncSession, slug: str) -> dict[str, Any] | None:
    res = await db.execute(
        sa.select(WorkflowTemplate).where(WorkflowTemplate.slug == slug)
    )
    t = res.scalar_one_or_none()
    return _template_to_dict(t) if t else None


async def install_template(
    db: AsyncSession,
    tenant_id: UUID,
    slug: str,
    *,
    created_by: UUID | None = None,
    name_override: str | None = None,
) -> dict[str, Any]:
    """Crea un Workflow real del tenant a partir de la plantilla.

    Si ya existe un Workflow con el mismo nombre en el tenant, le añade
    un sufijo numérico para evitar colisión.
    Incrementa `downloads_count` de la plantilla.
    """
    res = await db.execute(
        sa.select(WorkflowTemplate).where(WorkflowTemplate.slug == slug)
    )
    t = res.scalar_one_or_none()
    if t is None:
        raise ValueError(f"Plantilla no encontrada: {slug}")

    proposed_name = name_override or t.name
    final_name = await _ensure_unique_name(db, tenant_id, proposed_name)

    wf = Workflow(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        created_by=created_by,
        name=final_name,
        description=t.description,
        is_active=False,  # creado inactivo — el usuario lo activa cuando esté listo
        trigger_type=t.trigger_type,
        trigger_config=dict(t.trigger_config or {}),
        action_type=t.action_type,
        action_config=dict(t.action_config or {}),
        execution_mode=t.execution_mode,
        compiled_steps=list(t.compiled_steps) if t.compiled_steps else None,
    )
    db.add(wf)
    t.downloads_count = (t.downloads_count or 0) + 1
    await db.commit()
    await db.refresh(wf)

    return {
        "workflow_id": str(wf.id),
        "name": wf.name,
        "source_template_slug": t.slug,
        "is_active": False,
    }


async def _ensure_unique_name(
    db: AsyncSession, tenant_id: UUID, base_name: str
) -> str:
    """Si ya existe un workflow con `base_name` en el tenant, añade ` (n)`."""
    res = await db.execute(
        sa.select(Workflow.name).where(
            Workflow.tenant_id == tenant_id,
            Workflow.name.like(f"{base_name}%"),
        )
    )
    taken = {row[0] for row in res.all()}
    if base_name not in taken:
        return base_name
    for n in range(2, 100):
        candidate = f"{base_name} ({n})"
        if candidate not in taken:
            return candidate
    return f"{base_name} ({uuid.uuid4().hex[:6]})"
