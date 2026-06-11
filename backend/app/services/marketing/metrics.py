"""Analítica de posts de marketing: sincronización y agregación de métricas.

El publisher guarda `platform_post_id` al publicar; aquí consultamos las métricas
públicas de cada post a su red y persistimos un snapshot diario
(`scheduled_post_metrics`). La obtención real depende de tokens vigentes de las
redes (vía OAuth) — si falla, se omite ese post sin romper el job.
"""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_current_tenant
from app.db.base import AsyncSessionLocal
from app.db.models.marketing import ScheduledPost, ScheduledPostMetrics, SocialAccount
from app.services.marketing.oauth_tokens import ensure_valid_token

logger = logging.getLogger(__name__)

_METRIC_KEYS = ("impressions", "reach", "likes", "comments", "shares", "clicks")
_ZERO = dict.fromkeys(_METRIC_KEYS, 0)


async def fetch_post_metrics(
    platform: str, token: str, platform_post_id: str, account_id: str | None = None
) -> dict | None:
    """Consulta las métricas públicas de un post ya publicado. None si falla."""
    try:
        if platform == "twitter":
            return await _fetch_twitter(token, platform_post_id)
        if platform == "facebook":
            return await _fetch_facebook(token, platform_post_id)
        if platform == "instagram":
            return await _fetch_instagram(token, platform_post_id)
        # linkedin: socialActions requiere permisos adicionales — pendiente.
        return None
    except Exception as e:  # red/timeout/parseo → sin métricas esta vuelta
        logger.warning("[METRICS] %s post %s: %s", platform, platform_post_id, e)
        return None


async def _fetch_twitter(token: str, post_id: str) -> dict | None:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"https://api.twitter.com/2/tweets/{post_id}",
            params={"tweet.fields": "public_metrics"},
            headers={"Authorization": f"Bearer {token}"},
        )
    if r.status_code != 200:
        return None
    m = (r.json().get("data") or {}).get("public_metrics") or {}
    return {
        **_ZERO,
        "impressions": int(m.get("impression_count", 0)),
        "likes": int(m.get("like_count", 0)),
        "comments": int(m.get("reply_count", 0)),
        "shares": int(m.get("retweet_count", 0)) + int(m.get("quote_count", 0)),
    }


async def _fetch_facebook(token: str, post_id: str) -> dict | None:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"https://graph.facebook.com/v18.0/{post_id}",
            params={
                "fields": "likes.summary(true),comments.summary(true),shares",
                "access_token": token,
            },
        )
    if r.status_code != 200:
        return None
    d = r.json()
    likes = (d.get("likes") or {}).get("summary", {}).get("total_count", 0)
    comments = (d.get("comments") or {}).get("summary", {}).get("total_count", 0)
    shares = (d.get("shares") or {}).get("count", 0)
    return {**_ZERO, "likes": int(likes), "comments": int(comments), "shares": int(shares)}


async def _fetch_instagram(token: str, media_id: str) -> dict | None:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"https://graph.facebook.com/v18.0/{media_id}",
            params={"fields": "like_count,comments_count", "access_token": token},
        )
        ins = await client.get(
            f"https://graph.facebook.com/v18.0/{media_id}/insights",
            params={"metric": "impressions,reach", "access_token": token},
        )
    if r.status_code != 200:
        return None
    d = r.json()
    out = {
        **_ZERO,
        "likes": int(d.get("like_count", 0)),
        "comments": int(d.get("comments_count", 0)),
    }
    if ins.status_code == 200:
        for item in ins.json().get("data", []):
            name = item.get("name")
            vals = item.get("values") or []
            if name in ("impressions", "reach") and vals:
                out[name] = int(vals[0].get("value", 0))
    return out


async def _upsert_metrics(
    db: AsyncSession, post: ScheduledPost, metrics: dict, day: date
) -> None:
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


async def sync_all_post_metrics() -> None:
    """Job diario: actualiza el snapshot de métricas de los posts publicados."""
    try:
        await _sync_all_post_metrics()
    except Exception as e:
        logger.error("[METRICS] Error en sync_all_post_metrics: %s", e)


async def _sync_all_post_metrics() -> None:
    today = datetime.now(UTC).date()
    async with AsyncSessionLocal() as db:
        set_current_tenant(None)
        result = await db.execute(
            select(ScheduledPost).where(
                ScheduledPost.status == "published",
                ScheduledPost.platform_post_id.isnot(None),
            )
        )
        posts = result.scalars().all()
        updated = 0
        for post in posts:
            set_current_tenant(str(post.tenant_id))
            acc = await db.execute(
                select(SocialAccount).where(SocialAccount.id == post.social_account_id)
            )
            account = acc.scalar_one_or_none()
            if not account:
                continue
            token = await ensure_valid_token(account, db)
            if not token:
                continue
            metrics = await fetch_post_metrics(
                post.platform, token, post.platform_post_id, account.account_id
            )
            if metrics is None:
                continue
            await _upsert_metrics(db, post, metrics, today)
            updated += 1
        set_current_tenant(None)
        await db.commit()
        if posts:
            logger.info(
                "[METRICS] %d/%d posts con métricas actualizadas.", updated, len(posts)
            )


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
