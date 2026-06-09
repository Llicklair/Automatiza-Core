"""Tests de la resolución del Page token de Facebook en el callback OAuth.

Meta no permite publicar en perfiles personales: al conectar Facebook hay que
cambiar el user token por el Page token de una página gestionada. Cubre el
camino feliz, sin páginas y error del endpoint. httpx mockeado por URL.
"""
import pytest
from fastapi import HTTPException

from app.services.marketing import oauth


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


class _RoutingClient:
    """httpx.AsyncClient falso que responde según un substring de la URL."""

    def __init__(self, routes):
        self._routes = routes  # list[(substr, status, payload)]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, **kwargs):
        for sub, status, payload in self._routes:
            if sub in url:
                return _FakeResponse(status, payload)
        return _FakeResponse(404, {"error": "unmatched url"})


def _mock(monkeypatch, routes):
    monkeypatch.setattr(
        oauth.httpx, "AsyncClient",
        lambda *a, **k: _RoutingClient(routes),
    )


class TestResolveFacebookPage:
    async def test_returns_first_page_token(self, monkeypatch):
        _mock(monkeypatch, [
            ("oauth/access_token", 200, {"access_token": "long_user_token"}),
            ("me/accounts", 200, {"data": [
                {"id": "PAGE1", "name": "Mi Negocio", "access_token": "PAGE_TOKEN_1"},
                {"id": "PAGE2", "name": "Otra", "access_token": "PAGE_TOKEN_2"},
            ]}),
        ])
        page = await oauth._resolve_facebook_page("short_user_token")
        assert page == {"id": "PAGE1", "name": "Mi Negocio", "access_token": "PAGE_TOKEN_1"}

    async def test_raises_400_when_no_pages(self, monkeypatch):
        _mock(monkeypatch, [
            ("oauth/access_token", 200, {"access_token": "long_user_token"}),
            ("me/accounts", 200, {"data": []}),
        ])
        with pytest.raises(HTTPException) as ei:
            await oauth._resolve_facebook_page("u")
        assert ei.value.status_code == 400
        assert "página" in ei.value.detail.lower()

    async def test_raises_502_when_accounts_endpoint_fails(self, monkeypatch):
        _mock(monkeypatch, [
            ("oauth/access_token", 200, {"access_token": "long_user_token"}),
            ("me/accounts", 400, {"error": "permiso"}),
        ])
        with pytest.raises(HTTPException) as ei:
            await oauth._resolve_facebook_page("u")
        assert ei.value.status_code == 502

    async def test_falls_back_to_short_token_if_exchange_fails(self, monkeypatch):
        # Si el intercambio a larga duración falla, sigue con el token corto.
        captured = {}

        class _Capturing(_RoutingClient):
            async def get(self, url, **kwargs):
                if "me/accounts" in url:
                    captured["token"] = kwargs.get("params", {}).get("access_token")
                return await super().get(url, **kwargs)

        routes = [
            ("oauth/access_token", 500, {"error": "down"}),
            ("me/accounts", 200, {"data": [{"id": "P", "name": "N", "access_token": "PT"}]}),
        ]
        monkeypatch.setattr(
            oauth.httpx, "AsyncClient",
            lambda *a, **k: _Capturing(routes),
        )
        page = await oauth._resolve_facebook_page("short_user_token")
        assert page["access_token"] == "PT"
        assert captured["token"] == "short_user_token"  # cayó al token corto


class TestResolveInstagramAccount:
    async def test_returns_linked_ig_business_account(self, monkeypatch):
        _mock(monkeypatch, [
            ("oauth/access_token", 200, {"access_token": "long_user_token"}),
            ("me/accounts", 200, {"data": [
                {"id": "P1", "name": "Sin IG", "access_token": "PT1"},
                {"id": "P2", "name": "Con IG", "access_token": "PT2",
                 "instagram_business_account": {"id": "IG_USER_2", "username": "mi_ig"}},
            ]}),
        ])
        account = await oauth._resolve_instagram_account("u")
        # Toma el Page token de la página que tiene IG vinculada + el IG user id.
        assert account == {"id": "IG_USER_2", "name": "mi_ig", "access_token": "PT2"}

    async def test_raises_400_when_no_linked_ig(self, monkeypatch):
        _mock(monkeypatch, [
            ("oauth/access_token", 200, {"access_token": "long_user_token"}),
            ("me/accounts", 200, {"data": [{"id": "P", "name": "N", "access_token": "PT"}]}),
        ])
        with pytest.raises(HTTPException) as ei:
            await oauth._resolve_instagram_account("u")
        assert ei.value.status_code == 400
        assert "instagram" in ei.value.detail.lower()
