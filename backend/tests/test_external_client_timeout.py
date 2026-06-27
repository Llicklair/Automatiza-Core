"""Regresión L4: clientes httpx externos NO deben colgarse en la conexión.

Verifica que `httpx.AsyncClient` se construye SIEMPRE con un `timeout` no-None
en los dos clientes externos que carecían de él:

- `app.services.backup.b2_client`  → uploads/downloads de backups GRANDES:
  timeout generoso (`httpx.Timeout` con read/write >= 600s) para NO romper un
  upload legítimo, pero acotando la conexión.
- `app.services.migration.holded_client` → API REST paginada: `timeout == 30`.

Determinista, sin red: parchea `httpx.AsyncClient` en cada módulo con un
MagicMock que actúa como context manager async y captura los kwargs de
construcción. La respuesta HTTP se mockea para que el método complete sin red.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class _FakeAsyncClient:
    """Fake de `httpx.AsyncClient`: soporta `async with`, captura kwargs ctor,
    y devuelve `response` en get/post async."""

    def __init__(self, captured: dict, response: MagicMock, *args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        self.get = AsyncMock(return_value=response)
        self.post = AsyncMock(return_value=response)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _make_async_client_factory(captured: dict, response: MagicMock):
    """Factory para parchear `httpx.AsyncClient` con `_FakeAsyncClient`."""

    def _factory(*args, **kwargs):
        return _FakeAsyncClient(captured, response, *args, **kwargs)

    return _factory


# ── B2 (backup) ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_b2_authorize_constructs_client_with_generous_timeout():
    from app.services.backup import b2_client

    captured: dict = {}
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(
        return_value={
            "apiUrl": "https://api.example",
            "downloadUrl": "https://dl.example",
            "authorizationToken": "tok",
        }
    )

    creds = b2_client.B2Credentials(
        key_id="fake", application_key="fake", bucket_id="b", bucket_name="n",
    )

    with patch.object(
        b2_client.httpx, "AsyncClient",
        side_effect=_make_async_client_factory(captured, resp),
    ):
        await b2_client.authorize(creds)

    timeout = captured["kwargs"].get("timeout")
    assert timeout is not None, "b2 AsyncClient construido SIN timeout (cuelga)"
    assert isinstance(timeout, httpx.Timeout), "b2 debe usar httpx.Timeout generoso"
    # read/write generosos para uploads/downloads de backups grandes.
    assert timeout.read >= 600, f"read timeout demasiado corto: {timeout.read}"
    assert timeout.write >= 600, f"write timeout demasiado corto: {timeout.write}"
    # conexión acotada (no cuelga si el host es inalcanzable).
    assert timeout.connect is not None and timeout.connect <= 60


@pytest.mark.asyncio
async def test_b2_upload_file_constructs_client_with_generous_timeout():
    from app.services.backup import b2_client

    captured: dict = {}
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value={"fileId": "f1"})

    with patch.object(
        b2_client.httpx, "AsyncClient",
        side_effect=_make_async_client_factory(captured, resp),
    ):
        await b2_client.upload_file(
            upload_url="https://upload.example",
            upload_auth_token="tok",
            file_name="backup.enc",
            blob=b"x" * 1024,
        )

    timeout = captured["kwargs"].get("timeout")
    assert timeout is not None, "b2 upload_file AsyncClient SIN timeout"
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.read >= 600 and timeout.write >= 600


# ── Holded (migration) ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_holded_iter_contacts_constructs_client_with_timeout_30():
    from app.services.migration import holded_client
    from app.services.migration.holded_importer import HoldedCredentials

    captured: dict = {}
    resp = MagicMock()
    resp.status_code = 200
    # lista vacía → el iterador termina sin pedir más páginas.
    resp.json = MagicMock(return_value=[])
    resp.headers = {}

    creds = HoldedCredentials(api_key="fake-key")

    with patch.object(
        holded_client.httpx, "AsyncClient",
        side_effect=_make_async_client_factory(captured, resp),
    ):
        async for _ in holded_client.iter_contacts(creds):
            pass

    timeout = captured["kwargs"].get("timeout")
    assert timeout is not None, "holded AsyncClient construido SIN timeout (cuelga)"
    assert timeout == 30, f"holded timeout debe ser 30s, fue {timeout!r}"


@pytest.mark.asyncio
async def test_holded_iter_invoices_constructs_client_with_timeout_30():
    from app.services.migration import holded_client
    from app.services.migration.holded_importer import HoldedCredentials

    captured: dict = {}
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value=[])
    resp.headers = {}

    creds = HoldedCredentials(api_key="fake-key")

    with patch.object(
        holded_client.httpx, "AsyncClient",
        side_effect=_make_async_client_factory(captured, resp),
    ):
        async for _ in holded_client.iter_invoices(creds):
            pass

    timeout = captured["kwargs"].get("timeout")
    assert timeout is not None, "holded AsyncClient construido SIN timeout"
    assert timeout == 30
