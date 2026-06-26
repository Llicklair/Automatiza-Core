"""GET /api/v1/license/status: la clave de licencia NO se expone en claro.

El endpoint es público (allowlist del middleware de licencia) y la UI necesita
`valid`/`plan`, pero la clave completa no debe filtrarse a un visitante anónimo.
Verificamos que `key` viene enmascarada (solo últimos 4 caracteres).
"""
import pytest

import app.api.v1.routes.license as license_route

_FULL_KEY = "AUTOMATIZA-SECRET-LICENSE-AB12"


@pytest.mark.asyncio
async def test_status_masks_license_key(client, monkeypatch):
    # El endpoint llama a get_stored_key() importado en el módulo de la ruta.
    monkeypatch.setattr(license_route, "get_stored_key", lambda: _FULL_KEY)

    # Cliente SIN auth: el endpoint es público a propósito.
    res = await client.get("/api/v1/license/status")
    assert res.status_code == 200

    data = res.json()
    # valid y plan se mantienen (no rompemos la landing/activación).
    assert "valid" in data
    assert "plan" in data

    masked = data["key"]
    # No se filtra la clave completa.
    assert masked != _FULL_KEY
    # El prefijo sensible NO aparece.
    assert "AUTOMATIZA-SECRET" not in masked
    assert _FULL_KEY[:-4] not in masked
    # Solo se ven los últimos 4 caracteres.
    assert masked.endswith("AB12")
    assert "AB12" in masked
    assert len(masked) < len(_FULL_KEY)


@pytest.mark.asyncio
async def test_status_no_key_configured(client, monkeypatch):
    # Sin clave almacenada: no debe romper (None/"" pasa tal cual).
    monkeypatch.setattr(license_route, "get_stored_key", lambda: None)

    res = await client.get("/api/v1/license/status")
    assert res.status_code == 200
    data = res.json()
    assert data["key"] is None
