"""Destinatarios de email marketing: clientes del tenant con consentimiento.

Centraliza el filtro de destinatarios (antes duplicado 3 veces en la ruta).
"""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.crm import Client


def recipients_filter(tenant_id: UUID) -> tuple[Any, ...]:
    """Cláusulas WHERE: clientes del tenant con email no vacío y consentimiento."""
    return (
        Client.tenant_id == tenant_id,
        Client.email.isnot(None),
        Client.email != "",
        Client.marketing_consent.is_(True),
    )


async def count_recipients(tenant_id: UUID, db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(Client).where(*recipients_filter(tenant_id)))
    return result.scalar() or 0


async def list_recipients(tenant_id: UUID, db: AsyncSession) -> list[Client]:
    result = await db.execute(select(Client).where(*recipients_filter(tenant_id)))
    return list(result.scalars().all())
