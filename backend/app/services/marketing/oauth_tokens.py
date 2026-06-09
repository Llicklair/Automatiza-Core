"""Renovación de tokens OAuth de redes sociales antes de publicar.

Punto único: `ensure_valid_token` lo invoca el publisher, que a su vez es el
único choke point de publicación (scheduler + rutas manuales). Descifra el
access_token guardado y, si está caducado, lo renueva según la mecánica de cada
plataforma:

- Twitter/X y LinkedIn entregan `refresh_token` → grant_type=refresh_token.
  Twitter ROTA el refresh_token en cada uso → hay que persistir el nuevo.
- Facebook e Instagram NO dan refresh_token → se "renueva" re-intercambiando el
  propio access_token (fb_exchange_token / ig_refresh_token) por uno de larga
  duración.

Persiste el token renovado YA CIFRADO. No hace commit — lo hace el llamador.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.marketing import SocialAccount
from app.services.encryption import decrypt_str, encrypt_str

logger = logging.getLogger(__name__)

# Renueva con antelación para no publicar con un token a punto de morir.
_EXPIRY_BUFFER = timedelta(minutes=5)


async def ensure_valid_token(account: SocialAccount, db: AsyncSession) -> str | None:
    """Devuelve un access_token en claro y válido, renovándolo si hace falta.

    Devuelve None si el token caducó y no se pudo renovar (la cuenta necesita
    reconexión manual). No hace commit; el llamador commitea.
    """
    token = decrypt_str(account.access_token or "")
    if not token:
        return None

    if not _is_expiring(account.token_expires_at):
        return token

    new_data = await _refresh(account)
    if not new_data or not new_data.get("access_token"):
        logger.warning(
            "[MARKETING] No se pudo renovar token de %s (account=%s); requiere reconexión",
            account.platform, account.id,
        )
        return None

    new_token = new_data["access_token"]
    account.access_token = encrypt_str(new_token)
    new_refresh = new_data.get("refresh_token")
    if new_refresh:  # Twitter rota el refresh_token; otras no lo devuelven
        account.refresh_token = encrypt_str(new_refresh)
    expires_in = new_data.get("expires_in")
    if expires_in:
        account.token_expires_at = datetime.now(UTC) + timedelta(seconds=int(expires_in))
    await db.flush()
    logger.info("[MARKETING] Token de %s renovado (account=%s)", account.platform, account.id)
    return new_token


def _is_expiring(expires_at: datetime | None) -> bool:
    """True si el token caduca dentro del margen. None = desconocido → asumir válido."""
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC) + _EXPIRY_BUFFER


async def _refresh(account: SocialAccount) -> dict | None:
    if account.platform == "twitter":
        return await _refresh_twitter(account)
    if account.platform == "linkedin":
        return await _refresh_linkedin(account)
    if account.platform == "facebook":
        return await _refresh_facebook(account)
    if account.platform == "instagram":
        return await _refresh_instagram(account)
    return None


async def _refresh_twitter(account: SocialAccount) -> dict | None:
    refresh = decrypt_str(account.refresh_token or "")
    if not refresh:
        return None
    client_id = settings.TWITTER_CLIENT_ID
    client_secret = settings.TWITTER_CLIENT_SECRET
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://api.twitter.com/2/oauth2/token",
            data={"grant_type": "refresh_token", "refresh_token": refresh, "client_id": client_id},
            auth=(client_id, client_secret),
        )
    if r.status_code != 200:
        logger.warning("[MARKETING] Twitter refresh %s: %s", r.status_code, r.text[:200])
        return None
    return r.json()


async def _refresh_linkedin(account: SocialAccount) -> dict | None:
    refresh = decrypt_str(account.refresh_token or "")
    if not refresh:
        return None
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh,
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "client_secret": settings.LINKEDIN_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if r.status_code != 200:
        logger.warning("[MARKETING] LinkedIn refresh %s: %s", r.status_code, r.text[:200])
        return None
    return r.json()


async def _refresh_facebook(account: SocialAccount) -> dict | None:
    # Facebook no usa refresh_token: re-intercambia el access_token actual por
    # uno de larga duración (~60 días). Falla si el actual ya caducó del todo.
    current = decrypt_str(account.access_token or "")
    if not current:
        return None
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.FACEBOOK_CLIENT_ID,
                "client_secret": settings.FACEBOOK_CLIENT_SECRET,
                "fb_exchange_token": current,
            },
        )
    if r.status_code != 200:
        logger.warning("[MARKETING] Facebook refresh %s: %s", r.status_code, r.text[:200])
        return None
    return r.json()


async def _refresh_instagram(account: SocialAccount) -> dict | None:
    # Instagram extiende el long-lived token (token debe tener >24 h de vida).
    current = decrypt_str(account.access_token or "")
    if not current:
        return None
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://graph.instagram.com/refresh_access_token",
            params={"grant_type": "ig_refresh_token", "access_token": current},
        )
    if r.status_code != 200:
        logger.warning("[MARKETING] Instagram refresh %s: %s", r.status_code, r.text[:200])
        return None
    return r.json()
