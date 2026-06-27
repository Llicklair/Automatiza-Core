"""Tests de validacion de entrada (Pydantic) para recruitment.

H3: StatusUpdate.status como Literal -> status invalido devuelve 422.
H5: PositionCreate.salary_range_min/max con ge=0 + orden -> negativos o
    min>max devuelven 422.

Las lecturas (Response) no deben verse afectadas; el servicio sigue
validando estados (defensa en profundidad), pero Pydantic rechaza antes.
"""
from uuid import uuid4

import pytest

POSITIONS = "/api/v1/recruitment/positions"


def _candidate_status_url(candidate_id) -> str:
    return f"/api/v1/recruitment/candidates/{candidate_id}/status"


# ── H3: status (StatusUpdate Literal) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_status_invalido_devuelve_422(auth_client):
    """Un status fuera del Literal debe ser rechazado por Pydantic (422)."""
    url = _candidate_status_url(uuid4())
    resp = await auth_client.patch(url, json={"status": "invalido"})
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "valid_status", ["new", "reviewed", "shortlisted", "rejected", "hired"]
)
async def test_status_valido_no_es_422(auth_client, valid_status):
    """Un status valido NO debe dar 422 por validacion.

    Como el candidato no existe, el servicio devuelve 404 (LookupError);
    lo importante es que NO sea 422 (la capa Pydantic lo acepto).
    """
    url = _candidate_status_url(uuid4())
    resp = await auth_client.patch(url, json={"status": valid_status})
    assert resp.status_code != 422, resp.text


# ── H5: salary_range (PositionCreate) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_salario_negativo_devuelve_422(auth_client):
    payload = {
        "title": "Backend Engineer",
        "salary_range_min": -5,
    }
    resp = await auth_client.post(POSITIONS, json=payload)
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_salario_invertido_min_mayor_que_max_devuelve_422(auth_client):
    payload = {
        "title": "Backend Engineer",
        "salary_range_min": 5000,
        "salary_range_max": 1000,
    }
    resp = await auth_client.post(POSITIONS, json=payload)
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_salario_valido_no_es_422(auth_client):
    payload = {
        "title": "Backend Engineer",
        "salary_range_min": 1000,
        "salary_range_max": 5000,
    }
    resp = await auth_client.post(POSITIONS, json=payload)
    assert resp.status_code != 422, resp.text
