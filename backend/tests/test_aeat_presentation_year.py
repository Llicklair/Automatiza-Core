"""Validación de rango del parámetro `year` en endpoints AEAT.

Regresión: `year` se aceptaba sin rango y un año absurdo (0, 99999) se
persistía y acababa en el XML enviado a AEAT (`<Ejercicio>0</Ejercicio>`).
El endpoint asistido hermano ya validaba `ge=2020, le=2099`; aquí se replica
ese mismo rango en los 4 sitios que reciben `year` como entrada.

Solo se valida el RANGO de entrada (422 antes del servicio). Para años
válidos (2020-2099) el comportamiento es idéntico a antes.
"""

import pytest

PRESENTATIONS_URL = "/api/v1/aeat/presentations"
Q303_URL = "/api/v1/aeat/presentations/303-from-quarter"


def _body(year: int) -> dict:
    return {
        "model_code": "303",
        "year": year,
        "period": "1T",
        "xml_unsigned": "<Modelo/>",
        "environment": "preproduccion",
    }


def _year_in_detail(payload) -> bool:
    """True si algún error 422 menciona el campo `year`."""
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if not isinstance(detail, list):
        return False
    for err in detail:
        loc = err.get("loc", []) if isinstance(err, dict) else []
        if "year" in loc:
            return True
    return False


@pytest.mark.asyncio
async def test_create_presentation_year_zero_rejected(auth_client):
    resp = await auth_client.post(PRESENTATIONS_URL, json=_body(0))
    assert resp.status_code == 422, resp.text
    assert _year_in_detail(resp.json())


@pytest.mark.asyncio
async def test_create_presentation_year_too_high_rejected(auth_client):
    resp = await auth_client.post(PRESENTATIONS_URL, json=_body(99999))
    assert resp.status_code == 422, resp.text
    assert _year_in_detail(resp.json())


@pytest.mark.asyncio
async def test_create_presentation_valid_year_not_422_by_year(auth_client):
    """Año válido (2025): puede fallar por otra validación, pero NUNCA un 422
    causado por el campo `year`."""
    resp = await auth_client.post(PRESENTATIONS_URL, json=_body(2025))
    if resp.status_code == 422:
        assert not _year_in_detail(resp.json()), (
            "año válido 2025 no debe disparar 422 por el campo year"
        )


@pytest.mark.asyncio
async def test_303_from_quarter_year_zero_rejected(auth_client):
    """El Query param `year` del atajo 303 también valida el rango."""
    resp = await auth_client.post(
        Q303_URL, params={"quarter": 1, "year": 0, "environment": "preproduccion"}
    )
    assert resp.status_code == 422, resp.text
    assert _year_in_detail(resp.json())
