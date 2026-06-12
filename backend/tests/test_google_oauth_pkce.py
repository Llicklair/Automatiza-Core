"""PKCE (S256) en el flujo OAuth de Google — regresión.

Garantiza que generate_auth_url emite code_challenge S256, que exchange_code
reenvía el verifier, y que el state store transporta el verifier init→callback.
"""
import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import pytest

from app.integrations import google_oauth as g
from app.services.integration import service as svc


def test_generate_auth_url_emits_s256_challenge():
    url, state, verifier = g.generate_auth_url("tenant-123")
    q = parse_qs(urlparse(url).query)

    assert q["code_challenge_method"][0] == "S256"
    assert 43 <= len(verifier) <= 128
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    assert q["code_challenge"][0] == expected
    assert "=" not in q["code_challenge"][0]  # base64url sin padding
    assert state.startswith("tenant-123:")


def test_two_calls_produce_distinct_verifiers():
    _, _, v1 = g.generate_auth_url("t")
    _, _, v2 = g.generate_auth_url("t")
    assert v1 != v2  # un verifier por flujo


@pytest.mark.asyncio
async def test_exchange_code_forwards_verifier(monkeypatch):
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"access_token": "tok"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, _url, data=None, **_kw):
            captured.update(data or {})
            return FakeResp()

    monkeypatch.setattr(g.httpx, "AsyncClient", lambda *a, **k: FakeClient())

    await g.exchange_code("the-code", "verif-xyz")
    assert captured["code_verifier"] == "verif-xyz"
    assert captured["grant_type"] == "authorization_code"

    captured.clear()
    await g.exchange_code("the-code")  # sin verifier → no añade la clave
    assert "code_verifier" not in captured


def test_state_store_roundtrips_verifier():
    svc.set_oauth_state("st-google", "tenantA", "verif1")
    assert svc.pop_oauth_state("st-google") == ("tenantA", "verif1")

    svc.set_oauth_state("st-ms", "tenantB")  # Microsoft: sin PKCE
    assert svc.pop_oauth_state("st-ms") == ("tenantB", None)

    assert svc.pop_oauth_state("st-google") is None  # consumido (single-use)
