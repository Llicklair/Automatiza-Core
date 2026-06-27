"""Tests de validación de entrada para los endpoints /advisory.

Cubre dos arreglos:
- BUG A: `section` inválido debe dar 422 (antes caía silenciosamente a "fiscal").
- BUG B: `days_ahead` acotado (ge=1, le=365); fuera de rango -> 422.

Los casos 422 son deterministas: Pydantic valida ANTES de cualquier llamada de
red. Para los controles válidos solo se exige que NO sea 422 (puede ser 200 o
500 si el happy-path de /boe intenta una llamada de red real).
"""

import pytest

BOE = "/api/v1/advisory/boe"
GUIDES = "/api/v1/advisory/guides"
CALENDAR = "/api/v1/advisory/calendar"

SECCIONES_VALIDAS = ["fiscal", "laboral", "mercantil"]


# --- BUG A: /boe section ---------------------------------------------------


@pytest.mark.asyncio
async def test_boe_section_invalida_da_422(auth_client):
    resp = await auth_client.get(BOE, params={"section": "invalido"})
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("section", SECCIONES_VALIDAS)
async def test_boe_section_valida_no_es_422(auth_client, section):
    resp = await auth_client.get(BOE, params={"section": section})
    # No exigimos 200: el happy-path puede tocar red (BOE RSS) y devolver 500.
    # Lo importante es que la validación NO la rechace.
    assert resp.status_code != 422


# --- BUG A: /guides section ------------------------------------------------


@pytest.mark.asyncio
async def test_guides_section_invalida_da_422(auth_client):
    resp = await auth_client.get(GUIDES, params={"section": "invalido"})
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("section", SECCIONES_VALIDAS)
async def test_guides_section_valida_no_es_422(auth_client, section):
    resp = await auth_client.get(GUIDES, params={"section": section})
    assert resp.status_code != 422


# --- BUG B: /calendar days_ahead -------------------------------------------


@pytest.mark.asyncio
async def test_calendar_days_ahead_fuera_de_rango_da_422(auth_client):
    resp = await auth_client.get(CALENDAR, params={"days_ahead": 999999})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_calendar_days_ahead_cero_da_422(auth_client):
    resp = await auth_client.get(CALENDAR, params={"days_ahead": 0})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_calendar_days_ahead_valido_no_es_422(auth_client):
    resp = await auth_client.get(CALENDAR, params={"days_ahead": 90})
    assert resp.status_code != 422
