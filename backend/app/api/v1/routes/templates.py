"""
Endpoints para gestion de plantillas de documentos (facturas, nominas, excel).
GET/POST/PUT/DELETE + POST /preview
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.templates import (
    PreviewRequest,
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.middleware.rate_limit import limiter
from app.services import template_service as svc

logger = logging.getLogger(__name__)
router = APIRouter()

# Re-export for backward compatibility (used by agents / other services)
get_default_theme = svc.get_default_theme


# ── CRUD ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[TemplateResponse])
@limiter.limit("30/minute")
async def list_templates(
    request: Request,
    template_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await svc.list_templates(db, current_user.tenant_id, template_type)


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_template(
    request: Request,
    payload: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await svc.create_template(db, current_user.tenant_id, payload.model_dump())


@router.put("/{template_id}", response_model=TemplateResponse)
@limiter.limit("30/minute")
async def update_template(
    request: Request,
    template_id: UUID,
    payload: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await svc.update_template(
            db,
            template_id,
            current_user.tenant_id,
            payload.model_dump(exclude_unset=True),
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_template(
    request: Request,
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await svc.delete_template(db, template_id, current_user.tenant_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{template_id}/set-default", response_model=TemplateResponse)
@limiter.limit("30/minute")
async def set_default(
    request: Request,
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await svc.set_default(db, template_id, current_user.tenant_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Seed defaults ────────────────────────────────────────────────────────────


@router.post("/seed-defaults", response_model=list[TemplateResponse])
@limiter.limit("30/minute")
async def seed_defaults(
    request: Request,
    template_type: str = "invoice",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Crea plantillas preestablecidas para un tipo si el tenant no tiene ninguna."""
    try:
        return await svc.seed_defaults(db, current_user.tenant_id, template_type)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ── Preview ──────────────────────────────────────────────────────────────────


@router.post("/preview")
@limiter.limit("30/minute")
async def preview_template(
    request: Request,
    payload: PreviewRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Genera un PDF de muestra con la configuracion de tema enviada."""
    try:
        pdf_bytes = svc.generate_preview(payload.model_dump())
    except Exception:
        logger.exception("Error generando preview de plantilla")
        raise HTTPException(status_code=500, detail="Error interno al generar la vista previa")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=preview.pdf"},
    )
