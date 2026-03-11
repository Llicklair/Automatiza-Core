"""Microsoft OAuth 2.0 client for Outlook + OneDrive (Microsoft Graph)."""

import os
import secrets
from urllib.parse import urlencode

import httpx

MS_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

SCOPES = [
    "Mail.Read",
    "Mail.Send",
    "Files.ReadWrite",
    "User.Read",
    "offline_access",
]


def _client_id() -> str:
    return os.getenv("MICROSOFT_CLIENT_ID", "")


def _client_secret() -> str:
    return os.getenv("MICROSOFT_CLIENT_SECRET", "")


def _redirect_uri() -> str:
    return os.getenv(
        "MICROSOFT_REDIRECT_URI",
        "http://localhost:8080/api/v1/integrations/microsoft/callback",
    )


def generate_auth_url(tenant_id: str) -> tuple[str, str]:
    """Return (auth_url, state_token) for Microsoft OAuth consent screen."""
    state = f"{tenant_id}:{secrets.token_urlsafe(32)}"
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return f"{MS_AUTH_URL}?{urlencode(params)}", state


async def exchange_code(code: str) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            MS_TOKEN_URL,
            data={
                "code": code,
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Use refresh token to get a new access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            MS_TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        return resp.json()
