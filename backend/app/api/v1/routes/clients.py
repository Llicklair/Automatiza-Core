import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.v1.schemas.erp import (
    ClientCreate,
    ClientResponse,
    ClientUpdate,
    InvoiceResponse,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Client, Invoice, User
from app.middleware.rate_limit import limiter
from app.services.event_bus import emit_event

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/clients", response_model=list[ClientResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_clients(
    request: Request,
    skip: int = 0,
    limit: int = Query(default=50, le=100),
    client_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Client).where(Client.tenant_id == current_user.tenant_id)
    if client_type:
        query = query.where(Client.client_type == client_type)
    query = query.order_by(desc(Client.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED, tags=["erp"])
@limiter.limit("30/minute")
async def create_client(
    request: Request,
    payload: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_client = Client(
        tenant_id=current_user.tenant_id,
        **payload.model_dump()
    )
    db.add(new_client)
    try:
        await db.commit()
        await db.refresh(new_client)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un cliente con ese NIF o email")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error guardando cliente: %s", e)
        raise HTTPException(status_code=500, detail="Error al guardar el cliente")

    # Emitir evento para disparar automatizaciones (no crítico)
    try:
        await emit_event(
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            event_name="client_created",
            context={"client_id": str(new_client.id), "client_name": new_client.name, "nif": new_client.nif},
        )
    except Exception:
        logger.warning("emit_event client_created falló — no es crítico")

    return new_client


@router.patch("/clients/{client_id}", response_model=ClientResponse, tags=["erp"])
@limiter.limit("30/minute")
async def update_client(
    request: Request,
    client_id: UUID,
    payload: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == current_user.tenant_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(client, key, value)
    try:
        await db.commit()
        await db.refresh(client)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error actualizando cliente %s: %s", client_id, e)
        raise HTTPException(status_code=500, detail="Error al actualizar el cliente")
    return client


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
@limiter.limit("30/minute")
async def delete_client(
    request: Request,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == current_user.tenant_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    try:
        await db.delete(client)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error eliminando cliente %s: %s", client_id, e)
        raise HTTPException(status_code=500, detail="Error al eliminar el cliente")


@router.get("/clients/{client_id}/invoices", response_model=list[InvoiceResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_client_invoices(
    request: Request,
    client_id: UUID,
    skip: int = 0,
    limit: int = Query(default=100, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve todas las facturas de un cliente específico dentro del tenant."""
    # Verificar que el cliente pertenece al tenant
    client_result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.tenant_id == current_user.tenant_id,
        )
    )
    client = client_result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    query = (
        select(Invoice)
        .options(
            joinedload(Invoice.client),
            joinedload(Invoice.lines),
        )
        .where(
            Invoice.client_id == client_id,
            Invoice.tenant_id == current_user.tenant_id,
        )
        .order_by(desc(Invoice.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    # joinedload(Invoice.lines) devuelve posibles filas duplicadas; unique() es obligatorio
    return result.unique().scalars().all()
