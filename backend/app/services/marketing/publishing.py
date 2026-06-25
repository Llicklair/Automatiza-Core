"""Selección del proveedor de publicación de marketing (seam intercambiable).

Los consumidores (scheduler, rutas) llaman `get_publisher().publish_post(post, db)`
en vez de acoplarse a una implementación concreta. Hoy devuelve Zernio; cambiar de
proveedor (o volver atrás) es una sola línea aquí, sin tocar a los consumidores.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import ScheduledPost
from app.services.marketing.publisher_base import MarketingPublisher
from app.services.marketing.zernio_publisher import ZernioPublisher

logger = logging.getLogger(__name__)


def get_publisher() -> MarketingPublisher:
    """Devuelve el publisher de marketing activo."""
    return ZernioPublisher()


class PostAlreadyPublishedError(Exception):
    """El post ya estaba publicado (la ruta lo mapea a HTTP 409)."""


async def publish_single_post(
    post_id: UUID, tenant_id, db: AsyncSession
) -> tuple[ScheduledPost, bool] | None:
    """Publica un post no publicado del tenant. Devuelve `(post, ok)` con el post
    actualizado, o `None` si no existe. Lanza `PostAlreadyPublishedError` si ya estaba
    publicado. El publisher no lanza: deja el resultado en `post.status`/`error_message`.
    """
    result = await db.execute(
        select(ScheduledPost).where(
            ScheduledPost.id == post_id,
            ScheduledPost.tenant_id == tenant_id,
        )
    )
    post = result.scalar_one_or_none()
    if post is None:
        return None
    if post.status == "published":
        raise PostAlreadyPublishedError
    res = await get_publisher().publish_post(post, db)
    await db.commit()
    await db.refresh(post)
    return post, res.ok


async def publish_posts_batch(post_ids: list[UUID], tenant_id, db: AsyncSession) -> dict:
    """Publica varios posts no publicados. Devuelve `{published: [...], failed: [...]}`."""
    publisher = get_publisher()
    ok_ids: list[str] = []
    failed_ids: list[str] = []
    for pid in post_ids:
        result = await db.execute(
            select(ScheduledPost).where(
                ScheduledPost.id == pid,
                ScheduledPost.tenant_id == tenant_id,
                ScheduledPost.status != "published",
            )
        )
        post = result.scalar_one_or_none()
        if post is None:
            failed_ids.append(str(pid))
            continue
        # Commit por post (igual que publish_single_post): si el publisher de un
        # post posterior falla, no se revierte una publicación ya efectuada contra
        # la API externa. Un fallo de red no debe abortar el lote entero ni dejar
        # las listas published/failed mintiendo sobre el estado real en BD.
        try:
            res = await publisher.publish_post(post, db)
            await db.commit()
        except Exception:
            logger.exception("[MKT] Error publicando post %s; se marca como fallido", pid)
            await db.rollback()
            failed_ids.append(str(pid))
            continue
        (ok_ids if res.ok else failed_ids).append(str(pid))
    return {"published": ok_ids, "failed": failed_ids}
