import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.erp import (
    ClientCreate,
    ClientResponse,
    ClientUpdate,
    InvoiceResponse,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.sales import client as svc

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/clients", response_model=list[ClientResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_clients(
    request: Request,
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    client_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_clients(
        db, current_user.tenant_id, skip=skip, limit=limit, client_type=client_type
    )


@router.post(
    "/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED, tags=["erp"]
)
@limiter.limit("30/minute")
async def create_client(
    request: Request,
    payload: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.create_client(
            db, current_user.tenant_id, current_user.id, payload.model_dump()
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except RuntimeError as exc:
        logger.exception("Error creando cliente")
        raise HTTPException(status_code=500, detail="Error interno al crear el cliente") from exc


@router.patch("/clients/{client_id}", response_model=ClientResponse, tags=["erp"])
@limiter.limit("30/minute")
async def update_client(
    request: Request,
    client_id: UUID,
    payload: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_client(
            db, current_user.tenant_id, client_id, payload.model_dump(exclude_none=True)
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as exc:
        logger.exception("Error actualizando cliente")
        raise HTTPException(status_code=500, detail="Error interno al actualizar el cliente") from exc


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
@limiter.limit("30/minute")
async def delete_client(
    request: Request,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_client(db, current_user.tenant_id, client_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as exc:
        logger.exception("Error borrando cliente")
        raise HTTPException(status_code=500, detail="Error interno al eliminar el cliente") from exc


@router.get("/clients/{client_id}/invoices", response_model=list[InvoiceResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_client_invoices(
    request: Request,
    client_id: UUID,
    skip: int = 0,
    limit: int = Query(default=100, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve todas las facturas de un cliente específico dentro del tenant."""
    try:
        return await svc.list_client_invoices(
            db, current_user.tenant_id, client_id, skip=skip, limit=limit
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
