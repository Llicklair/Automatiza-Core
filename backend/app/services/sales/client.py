"""Business logic for Client CRUD operations."""

import logging
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.models import Client, Invoice
from app.services.event_bus import emit_event

logger = logging.getLogger(__name__)


async def list_clients(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 50,
    client_type: str | None = None,
) -> list[Client]:
    query = select(Client).where(Client.tenant_id == tenant_id)
    if client_type:
        query = query.where(Client.client_type == client_type)
    query = query.order_by(desc(Client.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_client(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    data: dict,
) -> Client:
    new_client = Client(tenant_id=tenant_id, **data)
    db.add(new_client)
    try:
        await db.commit()
        await db.refresh(new_client)
    except IntegrityError:
        await db.rollback()
        raise ValueError("Ya existe un cliente con ese NIF o email")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error guardando cliente: %s", e)
        raise RuntimeError("Error al guardar el cliente")

    # Emitir evento para disparar automatizaciones (no crítico)
    try:
        await emit_event(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            event_name="client_created",
            context={
                "client_id": str(new_client.id),
                "client_name": new_client.name,
                "nif": new_client.nif,
            },
        )
    except Exception:
        logger.warning("emit_event client_created falló — no es crítico")

    return new_client


async def update_client(
    db: AsyncSession,
    tenant_id: UUID,
    client_id: UUID,
    data: dict,
) -> Client:
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise LookupError("Cliente no encontrado")
    for key, value in data.items():
        setattr(client, key, value)
    try:
        await db.commit()
        await db.refresh(client)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error actualizando cliente %s: %s", client_id, e)
        raise RuntimeError("Error al actualizar el cliente")
    return client


async def delete_client(
    db: AsyncSession,
    tenant_id: UUID,
    client_id: UUID,
) -> None:
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise LookupError("Cliente no encontrado")
    try:
        await db.delete(client)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error eliminando cliente %s: %s", client_id, e)
        raise RuntimeError("Error al eliminar el cliente")


async def list_client_invoices(
    db: AsyncSession,
    tenant_id: UUID,
    client_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Invoice]:
    # Verificar que el cliente pertenece al tenant
    client_result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    )
    if not client_result.scalar_one_or_none():
        raise LookupError("Cliente no encontrado")

    query = (
        select(Invoice)
        .options(
            joinedload(Invoice.client),
            joinedload(Invoice.lines),
        )
        .where(
            Invoice.client_id == client_id,
            Invoice.tenant_id == tenant_id,
        )
        .order_by(desc(Invoice.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.unique().scalars().all())
