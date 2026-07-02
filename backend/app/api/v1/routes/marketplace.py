"""Rutas del marketplace de workflows (F3.10)."""

import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.base import get_db
from app.db.models.auth import User
from app.db.models.workflows import Workflow
from app.middleware.rate_limit import limiter
from app.services.workflow_marketplace import (
    WorkflowYamlError,
    export_workflow_to_yaml,
    get_template,
    import_yaml_as_workflow,
    install_template,
    list_templates,
    seed_official_templates,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/templates")
@limiter.limit("30/minute")
async def list_marketplace_templates(
    request: Request,
    category: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista plantillas del marketplace (filtrable por categoría)."""
    templates = await list_templates(db, category=category)
    return {"count": len(templates), "templates": templates}


@router.get("/templates/{slug}")
@limiter.limit("30/minute")
async def get_marketplace_template(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = await get_template(db, slug)
    if template is None:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada.")
    return template


@router.post("/templates/{slug}/install", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def install_marketplace_template(
    request: Request,
    slug: str,
    payload: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Instala la plantilla como Workflow real del tenant (inactivo por defecto)."""
    name_override = (payload or {}).get("name") if payload else None
    try:
        result = await install_template(
            db,
            current_user.tenant_id,
            slug,
            created_by=current_user.id,
            name_override=name_override,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result


@router.post("/templates/seed-official", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
async def seed_official(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Crea las plantillas oficiales que falten. Idempotente. Solo admin."""
    return await seed_official_templates(db)


@router.get("/workflows/{workflow_id}/export-yaml")
@limiter.limit("30/minute")
async def export_workflow_yaml(
    request: Request,
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta un Workflow del tenant a YAML para compartir o respaldar."""
    res = await db.execute(
        sa.select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == current_user.tenant_id,
        )
    )
    wf = res.scalar_one_or_none()
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow no encontrado.")
    return {"workflow_id": str(wf.id), "yaml": export_workflow_to_yaml(wf)}


@router.post("/workflows/import-yaml", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def import_workflow_yaml(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea un Workflow del tenant a partir de YAML pegado. Inactivo al inicio."""
    yaml_str = (payload or {}).get("yaml")
    if not yaml_str or not isinstance(yaml_str, str):
        raise HTTPException(status_code=422, detail="Campo 'yaml' requerido (string).")
    try:
        return await import_yaml_as_workflow(db, current_user.tenant_id, yaml_str, created_by=current_user.id)
    except WorkflowYamlError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
