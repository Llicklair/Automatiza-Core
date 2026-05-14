"""Rutas REST de notificaciones persistentes (UI.NOT)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import User
from app.services import notifications as svc

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: str
    kind: str
    title: str
    body: str | None
    payload: dict | None
    read_at: str | None
    created_at: str


class ListResponse(BaseModel):
    items: list[NotificationOut]
    unread_count: int


@router.get("", response_model=ListResponse)
async def list_endpoint(
    only_unread: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    items = await svc.list_notifications(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        only_unread=only_unread,
        limit=limit,
    )
    unread = await svc.count_unread(db, tenant_id=user.tenant_id, user_id=user.id)
    return {
        "items": [svc.to_dict(n) for n in items],
        "unread_count": unread,
    }


@router.patch("/{notification_id}/read")
async def mark_read_endpoint(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    changed = await svc.mark_read(
        db, tenant_id=user.tenant_id, notification_id=notification_id,
    )
    if not changed:
        raise HTTPException(status_code=404, detail="Notificación no encontrada o ya leída")
    await db.commit()
    return {"ok": True}


@router.post("/mark-all-read")
async def mark_all_read_endpoint(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    count = await svc.mark_all_read(db, tenant_id=user.tenant_id, user_id=user.id)
    await db.commit()
    return {"marked_read": count}
