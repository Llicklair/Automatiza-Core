"""Tests del cliente REST de Zernio (httpx MockTransport, sin red real).

Verifican el contrato con la API: cabecera de auth, cuerpo de `POST /posts`
(content + platforms + publishNow/mediaUrls) y la clasificación de errores
(transient en 429/5xx).
"""
import asyncio
import json

import httpx
import pytest

from app.services.marketing.zernio_client import ZernioClient, ZernioError


def _client(handler) -> ZernioClient:
    return ZernioClient("sk_test", transport=httpx.MockTransport(handler))


def test_create_post_publish_now_envia_contrato_correcto():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"post": {"_id": "p123", "status": "published"}})

    post = asyncio.run(
        _client(handler).create_post(
            content="hola", platform="instagram", account_id="a1",
            media_urls=["http://img/1.png"], publish_now=True,
        )
    )

    assert post.id == "p123"
    assert post.status == "published"
    body = captured["body"]
    assert body["content"] == "hola"
    assert body["platforms"] == [{"platform": "instagram", "accountId": "a1"}]
    assert body["publishNow"] is True
    assert body["mediaUrls"] == ["http://img/1.png"]
    assert captured["request"].headers["authorization"] == "Bearer sk_test"
    assert captured["request"].url.path.endswith("/posts")


def test_list_accounts_desempaqueta_data():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"_id": "a1", "platform": "instagram"}]})

    accounts = asyncio.run(_client(handler).list_accounts(profile_id="pf1"))
    assert accounts == [{"_id": "a1", "platform": "instagram"}]


def test_connect_url_devuelve_authurl():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/connect/instagram")
        return httpx.Response(200, json={"authUrl": "https://zernio.com/oauth/xyz"})

    url = asyncio.run(
        _client(handler).connect_url("instagram", "pf1", "https://app/cb")
    )
    assert url == "https://zernio.com/oauth/xyz"


def test_error_429_es_transient():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    with pytest.raises(ZernioError) as ei:
        asyncio.run(_client(handler).list_profiles())
    assert ei.value.status == 429
    assert ei.value.transient is True


def test_error_400_no_es_transient():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad request")

    with pytest.raises(ZernioError) as ei:
        asyncio.run(_client(handler).list_profiles())
    assert ei.value.status == 400
    assert ei.value.transient is False


def test_disconnect_account_hace_delete():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        return httpx.Response(200, json={"message": "Disconnected"})

    asyncio.run(_client(handler).disconnect_account("acc9"))
    assert captured["method"] == "DELETE"
    assert captured["path"].endswith("/accounts/acc9")


def test_api_key_obligatoria():
    with pytest.raises(ZernioError):
        ZernioClient("")
