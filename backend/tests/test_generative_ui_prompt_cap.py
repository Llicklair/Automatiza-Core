"""Tope de longitud de GenerateRequest.prompt (anti-DoS de coste LLM).

El prompt se concatena con contexto ERP y se envía al LLM; un payload de MB
dispararía el coste. El cap (max_length=8000) debe rechazar con 422 ANTES de
llegar al LLM. Un prompt normal NO debe fallar por longitud.
"""

import pytest

URL = "/api/v1/generative-ui/generate"


@pytest.mark.asyncio
async def test_prompt_excede_cap_devuelve_422(auth_client):
    """prompt de 8001 chars -> 422 (validación de entrada, antes del LLM)."""
    resp = await auth_client.post(URL, json={"prompt": "x" * 8001})
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_prompt_normal_no_es_422_por_longitud(auth_client):
    """CONTROL: un prompt normal no debe ser rechazado por longitud.

    Puede devolver otro código (502/504/500/201 según el estado del LLM),
    pero NUNCA 422 por la regla de max_length.
    """
    resp = await auth_client.post(
        URL, json={"prompt": "Dashboard de ventas del mes"}
    )
    assert resp.status_code != 422, resp.text
