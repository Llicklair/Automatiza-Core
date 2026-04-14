"""Albaranes (delivery notes) API routes."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.albaranes import (
    DeliveryNoteCreate,
    DeliveryNoteResponse,
    DeliveryNoteStatusUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.sales import albaran as svc

router = APIRouter(prefix="/albaranes", tags=["albaranes"])


@router.get("", response_model=List[DeliveryNoteResponse])
@limiter.limit("30/minute")
async def list_albaranes(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_albaranes(current_user.tenant_id, db)


@router.post("", response_model=DeliveryNoteResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_albaran(
    request: Request,
    payload: DeliveryNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.create_albaran(
        tenant_id=current_user.tenant_id,
        client_id=payload.client_id,
        entry_date=payload.date,
        notes=payload.notes,
        lines=payload.lines,
        db=db,
    )


@router.get("/{albaran_id}", response_model=DeliveryNoteResponse)
@limiter.limit("30/minute")
async def get_albaran(
    request: Request,
    albaran_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.get_albaran(albaran_id, current_user.tenant_id, db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{albaran_id}/status", response_model=DeliveryNoteResponse)
@limiter.limit("30/minute")
async def update_albaran_status(
    request: Request,
    albaran_id: UUID,
    payload: DeliveryNoteStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_albaran_status(
            albaran_id, current_user.tenant_id, payload.status, db
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{albaran_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_albaran(
    request: Request,
    albaran_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_albaran(albaran_id, current_user.tenant_id, db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{albaran_id}/pdf")
@limiter.limit("30/minute")
async def get_albaran_pdf(
    request: Request,
    albaran_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        pdf_bytes, albaran_number = await svc.get_albaran_pdf_data(
            albaran_id, current_user.tenant_id, db
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="albaran-{albaran_number}.pdf"'},
    )
