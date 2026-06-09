"""Publicación de posts en redes sociales."""

from __future__ import annotations

import logging
from collections import namedtuple
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import ScheduledPost, SocialAccount
from app.services.marketing.oauth_tokens import ensure_valid_token
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Resultado de publicar: `ok` = se publicó; `transient` = el fallo es reintentable
# (rate limit, error de servidor o de red). Permanente (token, contenido, config)
# → transient=False, no merece reintento.
PublishResult = namedtuple("PublishResult", ["ok", "transient"])

# Códigos HTTP que justifican reintentar más tarde.
_TRANSIENT_STATUS = {429, 500, 502, 503, 504}


async def publish_post(post: ScheduledPost, db: AsyncSession) -> PublishResult:
    """Publica el post en su red social y actualiza status en DB. Nunca lanza."""
    result = await db.execute(
        select(SocialAccount).where(SocialAccount.id == post.social_account_id)
    )
    account = result.scalar_one_or_none()
    if not account or not account.access_token:
        post.status = "failed"
        post.error_message = "Cuenta social no encontrada o sin token"
        return PublishResult(False, False)

    token = await ensure_valid_token(account, db)
    if not token:
        post.status = "failed"
        post.error_message = "Token caducado: reconecta la cuenta en Marketing → Cuentas"
        return PublishResult(False, False)

    transient = False
    try:
        ok, post_id, error, http_status = await _dispatch(
            post.platform, token, post.content, post.image_url, account.account_id
        )
        if not ok:
            transient = http_status in _TRANSIENT_STATUS
    except Exception as e:
        ok, post_id, error = False, None, str(e)
        transient = True  # red/timeout → reintentable

    if ok:
        post.status = "published"
        post.published_at = datetime.now(UTC)
        post.platform_post_id = post_id
        post.error_message = None
    else:
        post.status = "failed"
        post.error_message = (error or "Error desconocido")[:500]
    return PublishResult(ok, transient)


async def _dispatch(
    platform: str, token: str, content: str, image_url: str | None, account_id: str | None = None
) -> tuple[bool, str | None, str | None, int | None]:
    if platform == "twitter":
        return await _publish_twitter(token, content, image_url)
    elif platform == "linkedin":
        return await _publish_linkedin(token, content, image_url)
    elif platform == "facebook":
        return await _publish_facebook(token, content, image_url)
    elif platform == "instagram":
        return await _publish_instagram(token, content, image_url, account_id)
    else:
        return False, None, f"Plataforma no soportada: {platform}", None


async def _publish_twitter(token: str, content: str, image_url: str | None) -> tuple[bool, str | None, str | None, int | None]:
    payload: dict = {"text": content[:280]}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            "https://api.twitter.com/2/tweets",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
    if r.status_code in (200, 201):
        post_id = r.json().get("data", {}).get("id")
        return True, post_id, None, r.status_code
    return False, None, f"Twitter {r.status_code}: {r.text[:300]}", r.status_code


async def _publish_linkedin(token: str, content: str, image_url: str | None) -> tuple[bool, str | None, str | None, int | None]:
    # Obtener el URN del autor
    async with httpx.AsyncClient(timeout=15) as client:
        me = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )
    if me.status_code != 200:
        return False, None, f"LinkedIn userinfo {me.status_code}: {me.text[:200]}", me.status_code
    author_urn = f"urn:li:person:{me.json().get('sub', '')}"

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content[:3000]},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
    if r.status_code in (200, 201):
        post_id = r.headers.get("x-restli-id") or r.json().get("id")
        return True, post_id, None, r.status_code
    return False, None, f"LinkedIn {r.status_code}: {r.text[:300]}", r.status_code


async def _publish_facebook(token: str, content: str, image_url: str | None) -> tuple[bool, str | None, str | None, int | None]:
    # `token` es un Page access token (ver _resolve_facebook_page en routes):
    # con un token de Página, `/me/feed` apunta al feed de esa Página.
    params: dict = {"message": content[:63206], "access_token": token}
    if image_url:
        params["link"] = image_url
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post("https://graph.facebook.com/v18.0/me/feed", params=params)
    if r.status_code == 200:
        post_id = r.json().get("id")
        return True, post_id, None, r.status_code
    return False, None, f"Facebook {r.status_code}: {r.text[:300]}", r.status_code


async def _publish_instagram(token: str, content: str, image_url: str | None, ig_user_id: str | None) -> tuple[bool, str | None, str | None, int | None]:
    # Instagram Graph API: `token` es el Page token y `ig_user_id` el id de la
    # cuenta Business vinculada (ver _resolve_instagram_account en routes).
    if not image_url:
        return False, None, "Instagram requiere una imagen", None
    if not ig_user_id:
        return False, None, "Cuenta de Instagram sin id; reconecta la cuenta", None

    base = "https://graph.facebook.com/v18.0"
    async with httpx.AsyncClient(timeout=20) as client:
        # Paso 1: crear contenedor multimedia
        r1 = await client.post(
            f"{base}/{ig_user_id}/media",
            params={"image_url": image_url, "caption": content[:2200], "access_token": token},
        )
        if r1.status_code != 200:
            return False, None, f"Instagram container {r1.status_code}: {r1.text[:200]}", r1.status_code
        container_id = r1.json().get("id", "")

        # Paso 2: publicar contenedor
        r2 = await client.post(
            f"{base}/{ig_user_id}/media_publish",
            params={"creation_id": container_id, "access_token": token},
        )
    if r2.status_code == 200:
        post_id = r2.json().get("id")
        return True, post_id, None, r2.status_code
    return False, None, f"Instagram publish {r2.status_code}: {r2.text[:200]}", r2.status_code
