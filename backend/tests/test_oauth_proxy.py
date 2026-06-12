"""Tests del enrutado OAuth: proxy (Render) vs secret local (fallback)."""
import base64
import hashlib

import pytest
from fastapi import HTTPException

from app.services.marketing import oauth as oauth_mod


def _s256(verifier: str) -> str:
    return (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )


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


@pytest.mark.asyncio
class TestTwitterPKCE:
    async def test_oauth_url_emits_s256_challenge(self, monkeypatch):
        monkeypatch.setattr(oauth_mod.settings, "TWITTER_CLIENT_ID", "cid")
        state = "tw-state-1"
        url = oauth_mod._oauth_url("twitter", state)

        # Verifier real guardado (no viaja en la URL) y challenge = S256(verifier).
        verifier = oauth_mod._pkce_store[state][0]
        assert 43 <= len(verifier) <= 128
        assert "code_challenge_method=S256" in url
        assert f"code_challenge={_s256(verifier)}" in url
        assert "code_challenge=challenge" not in url  # ya no es el plain estático
        assert "method=plain" not in url
        oauth_mod._pkce_store.pop(state, None)

    async def test_exchange_forwards_verifier_via_proxy(self, monkeypatch):
        monkeypatch.setattr(oauth_mod.settings, "TWITTER_CLIENT_ID", "cid")
        monkeypatch.setattr(oauth_mod.settings, "OAUTH_PROXY_URL", "https://proxy.example/")
        monkeypatch.setattr(oauth_mod.httpx, "AsyncClient", _FakeClient)
        state = "tw-state-2"

        oauth_mod._oauth_url("twitter", state)  # guarda el verifier
        verifier = oauth_mod._pkce_store[state][0]
        _FakeClient.last_json = None

        await oauth_mod._exchange_token("twitter", "the-code", state)

        assert _FakeClient.last_url == "https://proxy.example/oauth/exchange"
        assert _FakeClient.last_json["code_verifier"] == verifier
        assert _FakeClient.last_json["platform"] == "twitter"
        # el verifier es de un solo uso: ya consumido del store
        assert state not in oauth_mod._pkce_store

    async def test_exchange_raises_when_flow_expired(self, monkeypatch):
        monkeypatch.setattr(oauth_mod.settings, "OAUTH_PROXY_URL", "https://proxy.example/")
        with pytest.raises(HTTPException) as exc:
            await oauth_mod._exchange_token("twitter", "the-code", "state-inexistente")
        assert exc.value.status_code == 400
