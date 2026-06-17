"""Analítica de posts de marketing — lectura/agregación de métricas locales.

Las métricas por post (snapshots diarios en `scheduled_post_metrics`) se agregan
por campaña aquí. La OBTENCIÓN de métricas desde las redes se hará vía la API de
Zernio (pendiente); hasta entonces, los totales reflejan lo que haya almacenado.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import ScheduledPost, ScheduledPostMetrics

_METRIC_KEYS = ("impressions", "reach", "likes", "comments", "shares", "clicks")
_ZERO = dict.fromkeys(_METRIC_KEYS, 0)


async def _upsert_metrics(
    db: AsyncSession, post: ScheduledPost, metrics: dict, day: date
) -> None:
    """Upsert del snapshot de métricas de un post para un día (idempotente).

    Punto de entrada para persistir métricas cuando se cablee Zernio Analytics.
    """
    existing = await db.execute(
        select(ScheduledPostMetrics).where(
            ScheduledPostMetrics.scheduled_post_id == post.id,
            ScheduledPostMetrics.metric_date == day,
        )
    )
    row = existing.scalar_one_or_none()
    if row is None:
        row = ScheduledPostMetrics(
            tenant_id=post.tenant_id, scheduled_post_id=post.id, metric_date=day
        )
        db.add(row)
    for k in _METRIC_KEYS:
        setattr(row, k, int(metrics.get(k, 0)))


async def get_campaign_metrics(db: AsyncSession, tenant_id, campaign_id) -> dict:
    """Agrega la última métrica conocida por post de una campaña.

    Devuelve totales agregados + detalle por post (con su última fecha de métrica).
    """
    posts_res = await db.execute(
        select(ScheduledPost).where(
            ScheduledPost.tenant_id == tenant_id,
            ScheduledPost.campaign_id == campaign_id,
        )
    )
    posts = posts_res.scalars().all()
    totals = dict(_ZERO)
    per_post = []
    for post in posts:
        m_res = await db.execute(
            select(ScheduledPostMetrics)
            .where(ScheduledPostMetrics.scheduled_post_id == post.id)
            .order_by(ScheduledPostMetrics.metric_date.desc())
            .limit(1)
        )
        m = m_res.scalar_one_or_none()
        vals = {k: getattr(m, k) for k in _METRIC_KEYS} if m else dict(_ZERO)
        for k in _METRIC_KEYS:
            totals[k] += vals[k]
        per_post.append(
            {
                "post_id": str(post.id),
                "platform": post.platform,
                "status": post.status,
                "metric_date": m.metric_date.isoformat() if m else None,
                **vals,
            }
        )
    return {
        "campaign_id": str(campaign_id),
        "num_posts": len(posts),
        "totals": totals,
        "posts": per_post,
    }
