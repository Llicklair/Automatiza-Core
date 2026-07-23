"""Albaranes (delivery notes) API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.albaranes import (
    DeliveryNoteCreate,
    DeliveryNoteResponse,
    DeliveryNoteStatusUpdate,
    DeliveryNoteUpdate,
    FacturarAlbaranesRequest,
)
from app.api.v1.schemas.erp import InvoiceResponse
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.sales import albaran as svc

router = APIRouter(prefix="/albaranes", tags=["albaranes"])


@router.get("", response_model=list[DeliveryNoteResponse])
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
        client_name=payload.client_name,
    )


@router.post("/facturar", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def facturar_albaranes(
    request: Request,
    payload: FacturarAlbaranesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Factura agrupada (tintorería T7): N albaranes del mismo cliente → una
    factura BORRADOR con enlaces N:M. Se revisa y emite desde Facturas (allí
    encadena VeriFactu). Un albarán ya facturado no se puede volver a facturar."""
    try:
        return await svc.facturar_albaranes(payload.albaran_ids, current_user.tenant_id, db, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{albaran_id}", response_model=DeliveryNoteResponse)
@limiter.limit("30/minute")
async def update_albaran(
    request: Request,
    albaran_id: UUID,
    payload: DeliveryNoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edición de albarán (tintorería T8). Entregado/anulado o facturado no
    se editan (solo rectificar); confirmado con stock descontado no admite
    cambio de líneas."""
    try:
        return await svc.update_albaran(
            albaran_id,
            current_user.tenant_id,
            db,
            client_id=payload.client_id,
            client_name=payload.client_name,
            entry_date=payload.date,
            notes=payload.notes,
            lines=payload.lines,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
            albaran_id,
            current_user.tenant_id,
            payload.status,
            db,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{albaran_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_albaran(
    request: Request,
    albaran_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_albaran(albaran_id, current_user.tenant_id, db, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{albaran_id}/ticket")
@limiter.limit("60/minute")
async def get_albaran_ticket(
    request: Request,
    albaran_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ticket-resguardo 80 mm del albarán (vertical tintorería): HTML
    autocontenido con QR del número para localizarlo al recoger. Imprimible en
    térmica de TPV o impresora normal."""
    from app.services.sales.albaran_ticket import build_albaran_ticket_html

    try:
        html = await build_albaran_ticket_html(albaran_id, current_user.tenant_id, db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/{albaran_id}/pdf")
@limiter.limit("30/minute")
async def get_albaran_pdf(
    request: Request,
    albaran_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        pdf_bytes, albaran_number = await svc.get_albaran_pdf_data(albaran_id, current_user.tenant_id, db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="albaran-{albaran_number}.pdf"'},
    )
