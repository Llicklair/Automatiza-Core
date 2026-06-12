"""Google OAuth 2.0 client for Gmail + Google Drive."""

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx

from app.core.config import settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
    "openid",
    "email",
]


def _client_id() -> str:
    return settings.GOOGLE_CLIENT_ID


def _client_secret() -> str:
    return settings.GOOGLE_CLIENT_SECRET


def _redirect_uri() -> str:
    return settings.GOOGLE_REDIRECT_URI


def _make_pkce() -> tuple[str, str]:
    """Genera (code_verifier, code_challenge) para PKCE S256 (RFC 7636).

    El challenge = base64url(sha256(verifier)) sin padding. El verifier (43-128
    chars) se guarda junto al state y se reenvía en exchange_code.
    """
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def generate_auth_url(tenant_id: str) -> tuple[str, str, str]:
    """Return (auth_url, state_token, code_verifier) for the consent screen.

    Usa PKCE (S256): protege el authorization code aunque sea interceptado y es
    el requisito para migrar a un cliente OAuth de tipo *Desktop* (cuyo
    client_secret Google trata como no confidencial). El llamador debe guardar el
    verifier junto al state y pasarlo a exchange_code en el callback.
    """
    state = f"{tenant_id}:{secrets.token_urlsafe(32)}"
    verifier, challenge = _make_pkce()
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}", state, verifier


async def exchange_code(code: str, code_verifier: str | None = None) -> dict:
    """Exchange authorization code for access + refresh tokens.

    code_verifier: el verifier PKCE devuelto por generate_auth_url. Es opcional
    por compatibilidad, pero el flujo normal siempre lo pasa.
    """
    data = {
        "code": code,
        "client_id": _client_id(),
        "client_secret": _client_secret(),
        "redirect_uri": _redirect_uri(),
        "grant_type": "authorization_code",
    }
    if code_verifier:
        data["code_verifier"] = code_verifier
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=data)
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Use refresh token to get a new access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        return resp.json()
