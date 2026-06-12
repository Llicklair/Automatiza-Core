"""Tests del enrutado OAuth: proxy (Render) vs secret local (fallback)."""
import pytest

from app.services.marketing import oauth as oauth_mod


class _Resp:
    status_code = 200
    text = ""

    def json(self):
        return {"access_token": "tok-proxy"}


class _FakeClient:
    last_url = None
    last_json = None

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **kwargs):
        _FakeClient.last_url = url
        _FakeClient.last_json = kwargs.get("json")
        return _Resp()


@pytest.mark.asyncio
class TestOAuthProxyRouting:
    async def test_exchange_uses_proxy_when_configured(self, monkeypatch):
        monkeypatch.setattr(oauth_mod.settings, "OAUTH_PROXY_URL", "https://proxy.example/")
        monkeypatch.setattr(oauth_mod.httpx, "AsyncClient", _FakeClient)
        _FakeClient.last_url = None

        res = await oauth_mod._exchange_token("facebook", "the-code")

        assert _FakeClient.last_url == "https://proxy.example/oauth/exchange"
        assert _FakeClient.last_json == {
            "platform": "facebook",
            "code": "the-code",
            "redirect_uri": oauth_mod._redirect_uri(),
        }
        assert res == {"access_token": "tok-proxy"}

    async def test_exchange_local_when_no_proxy(self, monkeypatch):
        monkeypatch.setattr(oauth_mod.settings, "OAUTH_PROXY_URL", "")
        monkeypatch.setattr(oauth_mod.settings, "FACEBOOK_CLIENT_ID", "cid")
        monkeypatch.setattr(oauth_mod.settings, "FACEBOOK_CLIENT_SECRET", "csecret")
        monkeypatch.setattr(oauth_mod.httpx, "AsyncClient", _FakeClient)
        _FakeClient.last_url = None

        await oauth_mod._exchange_token("facebook", "the-code")
        # Ruta local → llama directamente al endpoint de Meta, no al proxy.
        assert "graph.facebook.com" in _FakeClient.last_url
