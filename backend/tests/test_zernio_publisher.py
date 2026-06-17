"""Tests de `ZernioPublisher._do_publish` (sin BD: cuenta y cliente inyectados).

Verifican el contrato drop-in del publisher: éxito → status published +
platform_post_id; sin cuenta → failed no reintentable; 429 → failed reintentable;
400 → failed no reintentable.
"""
import asyncio
from types import SimpleNamespace

import httpx

from app.db.models.marketing import ScheduledPost
from app.services.marketing.zernio_client import ZernioClient
from app.services.marketing.zernio_publisher import ZernioPublisher


def _client(handler) -> ZernioClient:
    return ZernioClient("sk_test", transport=httpx.MockTransport(handler))


def _post() -> ScheduledPost:
    return ScheduledPost(
        platform="instagram", content="hola", image_url="http://img/1.png", status="scheduled"
    )


def test_publish_ok_marca_published():
    def handler(req):
        return httpx.Response(200, json={"post": {"_id": "zp9", "status": "published"}})

    post = _post()
    account = SimpleNamespace(account_id="acc1")
    res = asyncio.run(ZernioPublisher()._do_publish(post, account, _client(handler)))
    assert res.ok is True and res.transient is False
    assert post.status == "published"
    assert post.platform_post_id == "zp9"
    assert post.error_message is None


def test_publish_sin_cuenta_falla_no_transient():
    post = _post()
    res = asyncio.run(
        ZernioPublisher()._do_publish(post, None, _client(lambda r: httpx.Response(200, json={})))
    )
    assert res.ok is False and res.transient is False
    assert post.status == "failed"


def test_publish_429_es_transient():
    def handler(req):
        return httpx.Response(429, text="rate limited")

    post = _post()
    account = SimpleNamespace(account_id="acc1")
    res = asyncio.run(ZernioPublisher()._do_publish(post, account, _client(handler)))
    assert res.ok is False and res.transient is True
    assert post.status == "failed"


def test_publish_400_no_transient():
    def handler(req):
        return httpx.Response(400, text="contenido inválido")

    post = _post()
    account = SimpleNamespace(account_id="acc1")
    res = asyncio.run(ZernioPublisher()._do_publish(post, account, _client(handler)))
    assert res.ok is False and res.transient is False
    assert post.status == "failed"
