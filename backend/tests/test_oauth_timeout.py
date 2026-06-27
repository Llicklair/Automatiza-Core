"""Regresión L4 resiliencia: las llamadas httpx a endpoints OAuth/token externos
deben construir el cliente con timeout=30 para fallar-rápido en vez de colgar el
worker indefinidamente si el endpoint OAuth no responde.

Verifica de forma DETERMINISTA (sin red real) que cada función construye
`httpx.AsyncClient` con `timeout=30`, parcheando `httpx.AsyncClient` en el módulo
correspondiente con un MagicMock cuyo context-manager async devuelve un cliente
que responde un token fake.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_async_client_mock(json_payload: dict, status_code: int = 200):
    """Construye un mock de httpx.AsyncClient que soporta `async with` y devuelve
    un cliente cuyo .post/.get responde `json_payload`.

    Devuelve (async_client_cls_mock, client_instance_mock).
    """
    response = MagicMock()
    response.json = MagicMock(return_value=json_payload)
    response.raise_for_status = MagicMock(return_value=None)
    response.status_code = status_code

    client_instance = MagicMock()
    client_instance.post = AsyncMock(return_value=response)
    client_instance.get = AsyncMock(return_value=response)

    # `async with httpx.AsyncClient(...) as client:` → __aenter__ devuelve el cliente
    async_cm = MagicMock()
    async_cm.__aenter__ = AsyncMock(return_value=client_instance)
    async_cm.__aexit__ = AsyncMock(return_value=False)

    async_client_cls = MagicMock(return_value=async_cm)
    return async_client_cls, client_instance


@pytest.mark.asyncio
async def test_google_exchange_code_uses_timeout_30():
    from app.integrations import google_oauth

    cls_mock, _ = _make_async_client_mock({"access_token": "fake", "refresh_token": "r"})
    with patch.object(google_oauth.httpx, "AsyncClient", cls_mock):
        result = await google_oauth.exchange_code("auth-code", "verifier")

    assert result["access_token"] == "fake"
    assert cls_mock.call_count == 1
    assert cls_mock.call_args.kwargs["timeout"] == 30


@pytest.mark.asyncio
async def test_google_refresh_access_token_uses_timeout_30():
    from app.integrations import google_oauth

    cls_mock, _ = _make_async_client_mock({"access_token": "fresh"})
    with patch.object(google_oauth.httpx, "AsyncClient", cls_mock):
        result = await google_oauth.refresh_access_token("refresh-token")

    assert result["access_token"] == "fresh"
    assert cls_mock.call_count == 1
    assert cls_mock.call_args.kwargs["timeout"] == 30


@pytest.mark.asyncio
async def test_microsoft_exchange_code_uses_timeout_30():
    from app.integrations import microsoft_oauth

    cls_mock, _ = _make_async_client_mock({"access_token": "fake", "refresh_token": "r"})
    with patch.object(microsoft_oauth.httpx, "AsyncClient", cls_mock):
        result = await microsoft_oauth.exchange_code("auth-code")

    assert result["access_token"] == "fake"
    assert cls_mock.call_count == 1
    assert cls_mock.call_args.kwargs["timeout"] == 30


@pytest.mark.asyncio
async def test_microsoft_refresh_access_token_uses_timeout_30():
    from app.integrations import microsoft_oauth

    cls_mock, _ = _make_async_client_mock({"access_token": "fresh"})
    with patch.object(microsoft_oauth.httpx, "AsyncClient", cls_mock):
        result = await microsoft_oauth.refresh_access_token("refresh-token")

    assert result["access_token"] == "fresh"
    assert cls_mock.call_count == 1
    assert cls_mock.call_args.kwargs["timeout"] == 30


@pytest.mark.asyncio
async def test_get_oauth_access_token_uses_timeout_30():
    """El chequeo de token vivo en service.get_oauth_access_token (invocado en CADA
    operación de email/drive) debe usar timeout=30. Parcheamos las dependencias de
    DB/credenciales para aislar la construcción del cliente httpx.
    """
    from app.services.integration import service

    integration = MagicMock()
    integration.is_active = True
    integration.encrypted_credentials = "enc"

    # status 200 → no entra en la rama de refresh, devuelve el access_token cargado
    import httpx as real_httpx

    cls_mock, _ = _make_async_client_mock({}, status_code=200)

    with (
        patch.object(service, "get_integration", AsyncMock(return_value=integration)),
        patch.object(
            service,
            "decrypt_credentials",
            MagicMock(return_value={"access_token": "tok", "refresh_token": "r"}),
        ),
        patch.object(real_httpx, "AsyncClient", cls_mock),
    ):
        result = await service.get_oauth_access_token(MagicMock(), "tenant-1", "gmail")

    assert result == "tok"
    assert cls_mock.call_count == 1
    assert cls_mock.call_args.kwargs["timeout"] == 30
