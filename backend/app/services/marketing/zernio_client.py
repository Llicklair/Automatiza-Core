"""Cliente REST fino para la API de Zernio (social / mensajería / ads).

BYO: cada usuario trae su propia API key (`sk_...`). Este cliente NO sabe de la BD;
recibe la `api_key` y habla con `https://zernio.com/api/v1`. Lo consume
`ZernioPublisher`, que resuelve la key del usuario.

Docs: https://docs.zernio.com  ·  Auth: `Authorization: Bearer sk_...`
Modelo: Profile → Account(s) → Posts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Códigos HTTP que justifican reintentar más tarde (rate limit / errores de servidor).
_TRANSIENT_STATUS = {429, 500, 502, 503, 504}


class ZernioError(Exception):
    """Error de la API de Zernio. `transient=True` → el fallo es reintentable."""

    def __init__(self, message: str, *, status: int | None = None, transient: bool = False):
        super().__init__(message)
        self.status = status
        self.transient = transient


@dataclass
class ZernioPost:
    id: str
    status: str
    raw: dict


class ZernioClient:
    """Cliente async fino. Una instancia por API key (por usuario)."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not api_key:
            raise ZernioError("Falta la API key de Zernio")
        self._api_key = api_key
        self._base = (base_url or settings.ZERNIO_API_BASE).rstrip("/")
        self._timeout = timeout
        self._transport = transport  # inyectable en tests (httpx.MockTransport)

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kw) -> dict:
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                r = await client.request(method, url, headers=self._headers, **kw)
        except httpx.HTTPError as e:
            raise ZernioError(f"Red/timeout hablando con Zernio: {e}", transient=True) from e
        if r.status_code >= 400:
            raise ZernioError(
                f"Zernio {r.status_code}: {r.text[:300]}",
                status=r.status_code,
                transient=r.status_code in _TRANSIENT_STATUS,
            )
        try:
            return r.json()
        except ValueError:
            return {}

    # ── Perfiles y cuentas ────────────────────────────────────────────────────

    async def list_profiles(self) -> list[dict]:
        data = await self._request("GET", "/profiles")
        return data.get("data") or data.get("profiles") or []

    async def list_accounts(self, profile_id: str | None = None) -> list[dict]:
        params = {"profileId": profile_id} if profile_id else None
        data = await self._request("GET", "/accounts", params=params)
        return data.get("data") or data.get("accounts") or []

    async def connect_url(self, platform: str, profile_id: str, redirect_url: str) -> str:
        """Devuelve el `authUrl` de OAuth alojado por Zernio al que redirigir al usuario."""
        data = await self._request(
            "GET",
            f"/connect/{platform}",
            params={"profileId": profile_id, "redirect_url": redirect_url},
        )
        return data.get("authUrl") or data.get("url") or ""

    async def disconnect_account(self, account_id: str) -> dict:
        """Desconecta y elimina una cuenta social en Zernio (libera el hueco del plan).

        DELETE /accounts/{accountId} (operationId deleteAccount).
        """
        return await self._request("DELETE", f"/accounts/{account_id}")

    # ── Publicación ───────────────────────────────────────────────────────────

    async def create_post(
        self,
        *,
        content: str,
        platform: str,
        account_id: str,
        media_urls: list[str] | None = None,
        publish_now: bool = False,
        is_draft: bool = False,
        scheduled_at: str | None = None,
    ) -> ZernioPost:
        body: dict = {
            "content": content,
            "platforms": [{"platform": platform, "accountId": account_id}],
        }
        if media_urls:
            body["mediaUrls"] = media_urls
        if publish_now:
            body["publishNow"] = True
        elif is_draft:
            body["isDraft"] = True
        elif scheduled_at:
            body["scheduledAt"] = scheduled_at

        data = await self._request("POST", "/posts", json=body)
        post = data.get("post") or data.get("data") or data
        return ZernioPost(
            id=str(post.get("_id") or post.get("id") or ""),
            status=str(post.get("status") or ""),
            raw=post if isinstance(post, dict) else {},
        )

    # ── Analítica ─────────────────────────────────────────────────────────────

    async def get_analytics(self, *, platform: str, from_date: str, to_date: str) -> dict:
        return await self._request(
            "GET",
            "/analytics",
            params={"platform": platform, "fromDate": from_date, "toDate": to_date},
        )
