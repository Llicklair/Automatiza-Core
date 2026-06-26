"""Regresión: la transferencia de stock debe RECHAZAR quantity <= 0.

Antes, el schema no validaba `quantity` y el servicio aplicaba `abs()` silencioso,
de modo que `quantity=-5` se ejecutaba como `5`. Ahora `StockTransferRequest`
declara `Field(gt=0)`, así que la capa HTTP devuelve 422 (Pydantic) ANTES de
tocar la lógica de negocio. Por eso no hace falta sembrar producto/stock real.
"""
import uuid

import pytest
from httpx import AsyncClient

TRANSFER_URL = "/api/v1/inventory/transfer"


def _body(quantity: int) -> dict:
    """Body mínimo que pasa el parseo de tipos (UUIDs válidos)."""
    return {
        "product_id": str(uuid.uuid4()),
        "from_warehouse_id": str(uuid.uuid4()),
        "to_warehouse_id": str(uuid.uuid4()),
        "quantity": quantity,
    }


@pytest.mark.asyncio
async def test_transfer_negative_quantity_rejected(auth_client: AsyncClient):
    resp = await auth_client.post(TRANSFER_URL, json=_body(-5))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_transfer_zero_quantity_rejected(auth_client: AsyncClient):
    resp = await auth_client.post(TRANSFER_URL, json=_body(0))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_transfer_positive_quantity_not_422(auth_client: AsyncClient):
    """Control no-tautológico: un quantity > 0 NO se rechaza por validación.

    Puede dar 404/400 porque el producto/almacenes no existen, pero lo que
    importa es que NO sea un 422 de validación de `quantity`.
    """
    resp = await auth_client.post(TRANSFER_URL, json=_body(5))
    assert resp.status_code != 422
