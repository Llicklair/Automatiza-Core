"""Posts programados de marketing social: CRUD básico."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import ScheduledPost, SocialAccount


async def list_posts(
    tenant_id, db: AsyncSession, status_filter: Optional[str] = None
) -> list[ScheduledPost]:
    q = select(ScheduledPost).where(ScheduledPost.tenant_id == tenant_id)
    if status_filter:
        q = q.where(ScheduledPost.status == status_filter)
    q = q.order_by(
        ScheduledPost.scheduled_at.asc().nulls_last(),
        ScheduledPost.created_at.desc(),
    )
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_post(
    tenant_id,
    social_account_id: UUID,
    platform: str,
    content: str,
    image_url: Optional[str],
    campaign_id: Optional[UUID],
    scheduled_at,
    db: AsyncSession,
) -> ScheduledPost:
    """Crea un post programado/borrador.

    Raises LookupError si la cuenta social no existe o está inactiva.
    """
    acc = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == social_account_id,
            SocialAccount.tenant_id == tenant_id,
            SocialAccount.is_active.is_(True),
        )
    )
    if not acc.scalar_one_or_none():
        raise LookupError("Cuenta social no encontrada")

    post = ScheduledPost(
        tenant_id=tenant_id,
        social_account_id=social_account_id,
        campaign_id=campaign_id,
        platform=platform,
        content=content,
        image_url=image_url,
        scheduled_at=scheduled_at,
        status="scheduled" if scheduled_at else "draft",
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def delete_post(post_id: UUID, tenant_id, db: AsyncSession) -> bool:
    """Elimina un post no publicado.

    Devuelve False si no existe o ya está publicado.
    """
    result = await db.execute(
        select(ScheduledPost).where(
            ScheduledPost.id == post_id,
            ScheduledPost.tenant_id == tenant_id,
            ScheduledPost.status != "published",
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        return False
    await db.delete(post)
    await db.commit()
    return True


async def update_post(
    post_id: UUID,
    tenant_id,
    content: Optional[str],
    image_url: Optional[str],
    scheduled_at,
    db: AsyncSession,
) -> ScheduledPost | None:
    """Edita contenido, imagen o horario de un post borrador o programado.

    Devuelve None si no existe o ya está publicado.
    """
    result = await db.execute(
        select(ScheduledPost).where(
            ScheduledPost.id == post_id,
            ScheduledPost.tenant_id == tenant_id,
            ScheduledPost.status.in_(["draft", "scheduled"]),
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        return None

    if content is not None:
        post.content = content
    if image_url is not None:
        # Cadena vacía = "quitar imagen" → NULL
        post.image_url = image_url.strip() or None
    if scheduled_at is not None:
        post.scheduled_at = scheduled_at
        post.status = "scheduled"

    await db.commit()
    await db.refresh(post)
    return post
