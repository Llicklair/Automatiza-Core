"""Endpoint TPV: emitir la factura simplificada (F2) de una sesión cerrada."""
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestEmitirFacturaSimplificada:
    async def _closed_session(self, auth_client: AsyncClient) -> str:
        r = await auth_client.post("/api/v1/pos/sessions")
        assert r.status_code == 201, r.text
        sid = r.json()["id"]
        r = await auth_client.post(
            f"/api/v1/pos/sessions/{sid}/lines",
            json={"description": "Lavado", "quantity": 1, "unit_price": 100, "tax_percentage": 21},
        )
        assert r.status_code == 201, r.text
        r = await auth_client.post(f"/api/v1/pos/sessions/{sid}/checkout", json={"payment_method": "cash"})
        assert r.status_code == 200, r.text
        return sid

    async def test_emite_factura_de_sesion_cerrada(self, auth_client: AsyncClient):
        sid = await self._closed_session(auth_client)

        r = await auth_client.post(f"/api/v1/pos/sessions/{sid}/factura")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["invoice_type"] == "issued"
        assert data["amount_total"] == 121.0
        assert data["is_simplified"] is True
        # El campo del QR existe; es null en no_remission (sin registro encadenado).
        assert "verifactu" in data

    async def test_idempotente_devuelve_la_misma_factura(self, auth_client: AsyncClient):
        sid = await self._closed_session(auth_client)

        r1 = await auth_client.post(f"/api/v1/pos/sessions/{sid}/factura")
        r2 = await auth_client.post(f"/api/v1/pos/sessions/{sid}/factura")
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]

    async def test_sesion_abierta_da_400(self, auth_client: AsyncClient):
        r = await auth_client.post("/api/v1/pos/sessions")
        sid = r.json()["id"]

        r = await auth_client.post(f"/api/v1/pos/sessions/{sid}/factura")
        assert r.status_code == 400, r.text

    async def test_sesion_inexistente_da_404(self, auth_client: AsyncClient):
        r = await auth_client.post(f"/api/v1/pos/sessions/{uuid.uuid4()}/factura")
        assert r.status_code == 404, r.text

    async def test_sin_auth_da_401(self, client: AsyncClient):
        r = await client.post(f"/api/v1/pos/sessions/{uuid.uuid4()}/factura")
        assert r.status_code == 401
