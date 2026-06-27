"""
Regresión L2 (info-disclosure): las rutas de escritura de clients.py NO deben
filtrar el mensaje de una excepción interna (RuntimeError) en la respuesta 500.

Para cada endpoint (create/update/delete) se mockea la función de servicio que
llama la ruta con side_effect=RuntimeError("LEAK_MARKER_SECRET_99") y se verifica
que la respuesta sea 500 y que el marcador NO aparezca en el body ni en detail.
"""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

LEAK = "LEAK_MARKER_SECRET_99"


@pytest.mark.asyncio
async def test_create_client_500_no_leak(auth_client):
    with patch(
        "app.api.v1.routes.clients.svc.create_client",
        new=AsyncMock(side_effect=RuntimeError(LEAK)),
    ):
        resp = await auth_client.post("/api/v1/clients", json={"name": "Cliente Test"})

    assert resp.status_code == 500
    assert LEAK not in resp.text
    assert LEAK not in resp.json().get("detail", "")


@pytest.mark.asyncio
async def test_update_client_500_no_leak(auth_client):
    client_id = uuid4()
    with patch(
        "app.api.v1.routes.clients.svc.update_client",
        new=AsyncMock(side_effect=RuntimeError(LEAK)),
    ):
        resp = await auth_client.patch(
            f"/api/v1/clients/{client_id}", json={"name": "Nuevo Nombre"}
        )

    assert resp.status_code == 500
    assert LEAK not in resp.text
    assert LEAK not in resp.json().get("detail", "")


@pytest.mark.asyncio
async def test_delete_client_500_no_leak(auth_client):
    client_id = uuid4()
    with patch(
        "app.api.v1.routes.clients.svc.delete_client",
        new=AsyncMock(side_effect=RuntimeError(LEAK)),
    ):
        resp = await auth_client.delete(f"/api/v1/clients/{client_id}")

    assert resp.status_code == 500
    assert LEAK not in resp.text
    assert LEAK not in resp.json().get("detail", "")
