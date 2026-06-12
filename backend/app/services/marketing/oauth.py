"""OAuth de redes sociales: construcción de URLs de autorización, intercambio de
code por token y resolución de la cuenta a la que se publicará.

Lógica de protocolo OAuth extraída de la ruta para mantenerla fina y poder
testear este flujo sin levantar FastAPI. La ruta (`api/v1/routes/marketing.py`)
solo orquesta estos helpers y persiste el resultado.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time

import httpx
from fastapi import HTTPException

from app.core.config import settings

# ── PKCE (Twitter OAuth2 lo exige) ──────────────────────────────────────────────
# El verifier NO puede viajar en el `state` (iría en la misma redirect que el
# `code` y anularía PKCE). Se guarda aquí en memoria, keyed por state, entre la
# generación de la URL y el callback. Mismo proceso (backend local) → persiste
# entre ambas requests. Si el backend reinicia, el flujo caduca y se reconecta.
_PKCE_TTL = 600
_pkce_store: dict[str, tuple[str, float]] = {}


def _make_pkce() -> tuple[str, str]:
    """Devuelve (code_verifier, code_challenge S256) — base64url sin padding."""
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .decode("ascii")
        .rstrip("=")
    )
    return verifier, challenge


def _pkce_set(state: str, verifier: str) -> None:
    _pkce_store[state] = (verifier, time.time() + _PKCE_TTL)


def _pkce_pop(state: str) -> str | None:
    entry = _pkce_store.pop(state, None)
    if entry and entry[1] > time.time():
        return entry[0]
    return None


def _encode_state(platform: str, tenant_id: str) -> str:
    raw = f"{platform}|{tenant_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_state(state: str) -> tuple[str, str]:
    try:
        raw = base64.urlsafe_b64decode(state.encode()).decode()
        platform, tenant_id = raw.split("|", 1)
        return platform, tenant_id
    except Exception:
        raise HTTPException(status_code=400, detail="Estado OAuth inválido")


def _redirect_uri() -> str:
    return settings.OAUTH_REDIRECT_URI


def _proxy_url() -> str:
    """Base del proxy OAuth (Render) o cadena vacía si se usa el secret local."""
    return (settings.OAUTH_PROXY_URL or "").rstrip("/")


def _oauth_url(platform: str, state: str) -> str:
    # Instagram publica vía Instagram Graph API, que usa la misma app de Facebook.
    cred_platform = "facebook" if platform == "instagram" else platform
    client_id = getattr(settings, f"{cred_platform.upper()}_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(
            status_code=503,
            detail=f"OAuth para {platform} no configurado. Añade {cred_platform.upper()}_CLIENT_ID al .env",
        )
    redirect = _redirect_uri()

    # Twitter OAuth2 exige PKCE: verifier aleatorio por flujo, guardado keyed por
    # state (no viaja en la redirect); enviamos el challenge S256.
    twitter_challenge = ""
    if platform == "twitter":
        verifier, twitter_challenge = _make_pkce()
        _pkce_set(state, verifier)

    urls = {
        "instagram": (
            f"https://www.facebook.com/v18.0/dialog/oauth"
            f"?client_id={client_id}&redirect_uri={redirect}"
            f"&scope=instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement"
            f"&state={state}"
        ),
        "facebook": (
            f"https://www.facebook.com/v18.0/dialog/oauth"
            f"?client_id={client_id}&redirect_uri={redirect}"
            f"&scope=pages_show_list,pages_manage_posts,pages_read_engagement&state={state}"
        ),
        "linkedin": (
            f"https://www.linkedin.com/oauth/v2/authorization"
            f"?response_type=code&client_id={client_id}&redirect_uri={redirect}"
            f"&scope=openid+profile+w_member_social&state={state}"
        ),
        "twitter": (
            f"https://x.com/i/oauth2/authorize"
            f"?response_type=code&client_id={client_id}&redirect_uri={redirect}"
            f"&scope=tweet.write+users.read+offline.access"
            f"&state={state}&code_challenge={twitter_challenge}&code_challenge_method=S256"
        ),
    }
    return urls[platform]


async def _exchange_token(platform: str, code: str, state: str = "") -> dict:
    """Intercambia el authorization code por un access token."""
    redirect = _redirect_uri()
    proxy = _proxy_url()

    # Twitter: recupera el verifier PKCE generado al construir la URL. Si falta
    # (state expirado o backend reiniciado), el intercambio no puede completar PKCE.
    code_verifier: str | None = None
    if platform == "twitter":
        code_verifier = _pkce_pop(state)
        if not code_verifier:
            raise HTTPException(
                status_code=400,
                detail="Flujo OAuth de Twitter expirado. Vuelve a conectar la cuenta.",
            )

    if proxy:
        # El servidor (Render) guarda el client_secret y hace el intercambio.
        payload = {"platform": platform, "code": code, "redirect_uri": redirect}
        if code_verifier:
            payload["code_verifier"] = code_verifier
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(f"{proxy}/oauth/exchange", json=payload)
        if r.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Error {r.status_code} en proxy OAuth ({platform}): {r.text[:300]}",
            )
        return r.json()

    # Fallback local: intercambio con el client_secret de la app.
    cred_platform = "facebook" if platform == "instagram" else platform
    client_id = getattr(settings, f"{cred_platform.upper()}_CLIENT_ID", "")
    client_secret = getattr(settings, f"{cred_platform.upper()}_CLIENT_SECRET", "")

    async with httpx.AsyncClient(timeout=15) as client:
        if platform in ("instagram", "facebook"):
            r = await client.post(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect,
                    "code": code,
                },
            )
        elif platform == "linkedin":
            r = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        elif platform == "twitter":
            r = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect,
                    "code_verifier": code_verifier,
                },
                auth=(client_id, client_secret),
            )
        else:
            raise HTTPException(status_code=400, detail=f"Plataforma no soportada: {platform}")

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Error {r.status_code} al obtener token de {platform}: {r.text[:400]}")
    return r.json()


async def _fetch_profile(platform: str, access_token: str) -> tuple[str, str]:
    """Devuelve (account_id, account_name) desde la API de la plataforma."""
    async with httpx.AsyncClient(timeout=15) as client:
        if platform == "instagram":
            r = await client.get(
                "https://graph.instagram.com/me",
                params={"fields": "id,username", "access_token": access_token},
            )
            data = r.json()
            return data.get("id", ""), data.get("username", "")

        elif platform == "facebook":
            r = await client.get(
                "https://graph.facebook.com/me",
                params={"fields": "id,name", "access_token": access_token},
            )
            data = r.json()
            return data.get("id", ""), data.get("name", "")

        elif platform == "linkedin":
            r = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            data = r.json()
            return data.get("sub", ""), data.get("name", "")

        elif platform == "twitter":
            r = await client.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            data = r.json().get("data", {})
            return data.get("id", ""), data.get("name", "")

    return "", ""


async def _facebook_pages(user_token: str) -> list[dict]:
    """Intercambia el user token por uno de larga duración (60 días) y devuelve
    las páginas gestionadas. Cada página trae su Page token (larga duración, sin
    expiración) y, si la hay, su cuenta de Instagram Business vinculada."""
    proxy = _proxy_url()
    async with httpx.AsyncClient(timeout=15) as client:
        # 1) user token de larga duración. fb_exchange_token requiere el secret →
        # vía proxy si está configurado; si no, intercambio local.
        if proxy:
            lr = await client.post(f"{proxy}/oauth/fb-longtoken", json={"user_token": user_token})
            long_token = lr.json().get("access_token", user_token) if lr.status_code == 200 else user_token
        else:
            long = await client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.FACEBOOK_CLIENT_ID,
                    "client_secret": settings.FACEBOOK_CLIENT_SECRET,
                    "fb_exchange_token": user_token,
                },
            )
            long_token = long.json().get("access_token", user_token) if long.status_code == 200 else user_token
        # 2) páginas gestionadas (+ IG Business vinculada en una sola llamada).
        # Solo usa long_token (sin secret) → siempre local.
        pages = await client.get(
            "https://graph.facebook.com/v18.0/me/accounts",
            params={
                "fields": "id,name,access_token,instagram_business_account{id,username}",
                "access_token": long_token,
            },
        )
    if pages.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Error al listar páginas de Facebook: {pages.text[:200]}")
    return pages.json().get("data", [])


async def _resolve_facebook_page(user_token: str) -> dict:
    """Token de la primera Página de Facebook gestionada.

    Meta no permite publicar en perfiles personales vía API (se retiró en 2018):
    hay que publicar en una Página con su Page access token.
    """
    pages = await _facebook_pages(user_token)
    if not pages:
        raise HTTPException(
            status_code=400,
            detail="No gestionas ninguna página de Facebook. Meta no permite publicar en perfiles personales; crea o administra una página y reconecta.",
        )
    page = pages[0]
    return {"id": page.get("id", ""), "name": page.get("name", ""), "access_token": page.get("access_token", "")}


async def _resolve_instagram_account(user_token: str) -> dict:
    """Cuenta de Instagram Business vinculada a la primera página que tenga una.

    Publicar en Instagram exige una cuenta Business/Creator vinculada a una
    Página de Facebook; se publica con el Page token y el IG user id.
    """
    for page in await _facebook_pages(user_token):
        ig = page.get("instagram_business_account") or {}
        if ig.get("id"):
            return {
                "id": ig["id"],
                "name": ig.get("username") or page.get("name", ""),
                "access_token": page.get("access_token", ""),
            }
    raise HTTPException(
        status_code=400,
        detail="No hay ninguna cuenta de Instagram Business vinculada a tus páginas de Facebook. Vincula una cuenta Business/Creator a una página y reconecta.",
    )
