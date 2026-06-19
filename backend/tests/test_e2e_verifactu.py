"""E2E Veri*factu — flujo de usuario real (simulación local, sin AEAT).

A diferencia de `test_verify_endpoint.py` (que inserta el `VerifactuRecord` a
mano), aquí se ejercita el camino REAL del usuario por API:

    activar modo voluntary -> crear cliente -> emitir factura (POST + emitir)
    -> la cadena se engancha sola (maybe_append_verifactu_record)
    -> /verify público devuelve la huella con integridad OK
    -> una segunda factura enlaza la cadena (huella_anterior)

Blinda el flujo #1 de `tasks/iteraciones-cliente-real.md`.
"""
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import Tenant
from app.db.models.billing import VerifactuRecord
from app.services.billing.verifactu_mode import set_mode


async def _enable_voluntary(db: AsyncSession) -> Tenant:
    tenant = (await db.execute(select(Tenant))).scalars().first()
    assert tenant is not None and tenant.nif, "el tenant de test debe tener NIF"
    await set_mode(db, tenant_id=tenant.id, mode="voluntary")
    await db.flush()
    return tenant


async def _emit_invoice(ac: AsyncClient, client_id) -> dict:
    """Crea una factura y la emite (draft -> pending), como hace el usuario."""
    create = await ac.post(
        f"/api/v1/clients/{client_id}/invoices",
        json={
            "date": datetime.now().isoformat(),
            "status": "draft",
            "invoice_type": "issued",
            "lines": [
                {"description": "Servicio", "quantity": 1.0,
                 "unit_price": 100.0, "tax_percentage": 21.0},
            ],
        },
    )
    assert create.status_code == 201, create.text
    inv = create.json()
    patch = await ac.patch(
        f"/api/v1/invoices/{inv['id']}/status", json={"status": "pending"}
    )
    assert patch.status_code == 200, patch.text
    return inv


async def _records(db: AsyncSession) -> list[VerifactuRecord]:
    db.expire_all()
    # Orden de cadena = orden de creación. NO ordenar por `id` (UUID aleatorio):
    # devolvería los eslabones en orden arbitrario y el assert de la cadena
    # (recs[-1].huella_anterior == recs[-2].huella) fallaría ~50% → test flaky.
    res = await db.execute(select(VerifactuRecord).order_by(VerifactuRecord.created_at))
    return list(res.scalars().all())


@pytest.mark.asyncio
class TestVerifactuFlujoReal:
    async def test_emision_api_genera_huella_verificable(
        self, auth_client: AsyncClient, db: AsyncSession
    ):
        await _enable_voluntary(db)

        c = await auth_client.post(
            "/api/v1/clients",
            json={"name": "Cliente Veri", "nif": "A12345678", "email": "v@e.com"},
        )
        assert c.status_code == 201, c.text
        client_id = c.json()["id"]

        await _emit_invoice(auth_client, client_id)

        recs = await _records(db)
        assert recs, "modo voluntary: emitir una factura debe crear un VerifactuRecord"
        rec = recs[-1]
        assert rec.huella and len(rec.huella) == 64

        v = await auth_client.get(f"/api/v1/verify/{rec.huella}")
        assert v.status_code == 200, v.text
        body = v.json()
        assert body["integrity_ok"] is True
        assert body["nif_emisor"] == "B12345678"
        assert body["huella"] == rec.huella

    async def test_cadena_enlaza_dos_facturas(
        self, auth_client: AsyncClient, db: AsyncSession
    ):
        await _enable_voluntary(db)
        c = await auth_client.post(
            "/api/v1/clients",
            json={"name": "Cliente Veri2", "nif": "A87654321", "email": "v2@e.com"},
        )
        client_id = c.json()["id"]

        await _emit_invoice(auth_client, client_id)
        await _emit_invoice(auth_client, client_id)

        recs = await _records(db)
        assert len(recs) >= 2, "deberían existir dos eslabones en la cadena"
        assert recs[-1].huella_anterior == recs[-2].huella, (
            "la cadena Veri*factu debe enlazar huella_anterior con la huella previa"
        )

    async def test_no_remission_no_crea_cadena(
        self, auth_client: AsyncClient, db: AsyncSession
    ):
        # Default no_remission: emitir NO debe crear cadena local.
        c = await auth_client.post(
            "/api/v1/clients",
            json={"name": "Cliente Sin", "nif": "A11111111", "email": "s@e.com"},
        )
        client_id = c.json()["id"]
        await _emit_invoice(auth_client, client_id)

        assert await _records(db) == [], "en no_remission no debe crearse VerifactuRecord"
