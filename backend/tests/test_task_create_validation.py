"""Validación de entrada de TaskCreate (POST /api/v1/tasks).

Regresión: `domain` se persiste en VARCHAR(100) y `user_intent` se embebe en
el prompt del agente LLM. Sin tope de longitud, un domain > 100 chars provoca
un INSERT que revienta en BD (500) y un user_intent multi-MB es un DoS de coste
directo (se almacena y se manda al LLM). Ambos deben rechazarse con 422 en la
capa de validación (Pydantic), no llegar a BD ni al LLM.
"""

import pytest

_URL = "/api/v1/tasks"
# Cap de user_intent declarado en TaskCreate (Field(max_length=10000)).
_USER_INTENT_CAP = 10000


@pytest.mark.asyncio
async def test_domain_too_long_returns_422(auth_client):
    """domain de 101 chars (columna = VARCHAR(100)) -> 422, no 500 de BD."""
    resp = await auth_client.post(
        _URL,
        json={"domain": "x" * 101, "user_intent": "Crear factura para cliente X"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_user_intent_too_long_returns_422(auth_client):
    """user_intent de (cap+1) chars -> 422 (frena el DoS de coste del LLM)."""
    resp = await auth_client.post(
        _URL,
        json={"domain": "billing", "user_intent": "x" * (_USER_INTENT_CAP + 1)},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_normal_payload_not_rejected_by_length_validation(auth_client):
    """Control: domain corto + user_intent normal NO da 422 por longitud.

    El endpoint puede devolver 201/200/otro según el pipeline; lo único que
    aquí se garantiza es que la validación de longitud no lo bloquea (≠ 422).
    """
    resp = await auth_client.post(
        _URL,
        json={"domain": "billing", "user_intent": "Crear factura para cliente X"},
    )
    assert resp.status_code != 422, resp.text
