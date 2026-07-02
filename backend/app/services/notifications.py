"""Servicio de notificaciones persistentes (UI.NOT)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notifications import Notification

logger = logging.getLogger("services.notifications")

NotificationKind = Literal["info", "success", "warning", "error"]


async def create_notification(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    title: str,
    body: str | None = None,
    kind: NotificationKind = "info",
    user_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> Notification:
    """Persiste una notificación. Devuelve el registro creado."""
    record = Notification(
        tenant_id=tenant_id,
        user_id=user_id,
        kind=kind,
        title=title[:200],
        body=body,
        payload=payload,
    )
    db.add(record)
    await db.flush()
    return record


async def list_notifications(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID | None = None,
    only_unread: bool = False,
    limit: int = 50,
) -> list[Notification]:
    """Lista las notificaciones del tenant (opcional: del usuario), recientes primero."""
    query = select(Notification).where(Notification.tenant_id == tenant_id)
    if user_id is not None:
        # User-specific OR broadcast (user_id IS NULL).
        query = query.where((Notification.user_id == user_id) | (Notification.user_id.is_(None)))
    if only_unread:
        query = query.where(Notification.read_at.is_(None))
    query = query.order_by(desc(Notification.created_at)).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_unread(db: AsyncSession, *, tenant_id: UUID, user_id: UUID | None = None) -> int:
    """Cuenta no leídas — usado para el badge del bell."""
    query = select(func.count(Notification.id)).where(
        Notification.tenant_id == tenant_id,
        Notification.read_at.is_(None),
    )
    if user_id is not None:
        query = query.where((Notification.user_id == user_id) | (Notification.user_id.is_(None)))
    result = await db.execute(query)
    return int(result.scalar_one())


async def mark_read(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    notification_id: UUID,
    user_id: UUID | None = None,
) -> bool:
    """Marca una notificación como leída. Devuelve True si cambió.

    Si se pasa ``user_id``, solo afecta a notificaciones propias del usuario
    o broadcasts (``user_id IS NULL``): evita que un usuario marque leída la
    notificación privada de otro usuario del mismo tenant (IDOR intra-tenant).
    """
    stmt = (
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.tenant_id == tenant_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    if user_id is not None:
        stmt = stmt.where((Notification.user_id == user_id) | (Notification.user_id.is_(None)))
    result = await db.execute(stmt)
    return result.rowcount > 0


async def mark_all_read(db: AsyncSession, *, tenant_id: UUID, user_id: UUID | None = None) -> int:
    """Marca todas las no leídas como leídas. Devuelve cuántas cambiaron."""
    now = datetime.now(UTC)
    stmt = (
        update(Notification)
        .where(
            Notification.tenant_id == tenant_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
    )
    if user_id is not None:
        stmt = stmt.where((Notification.user_id == user_id) | (Notification.user_id.is_(None)))
    result = await db.execute(stmt)
    return result.rowcount


def to_dict(record: Notification) -> dict:
    return {
        "id": str(record.id),
        "kind": record.kind,
        "title": record.title,
        "body": record.body,
        "payload": record.payload,
        "read_at": record.read_at.isoformat() if record.read_at else None,
        "created_at": record.created_at.isoformat(),
    }
