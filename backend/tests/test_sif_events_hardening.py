"""Endurecimiento S del audit 2026-07-21 (P2/P3/P5).

- Settings declara VERIFACTU_SIF_* (antes pydantic los descartaba y la
  declaración imprimía siempre placeholders).
- Payload de eventos con los 8 campos del art. 13.1.c Orden HAC/1177/2024.
- Huso fijo Europe/Madrid en registros y eventos (no la tz del SO).
- Evento RESTAURACION registrable y encadenado.
- verify_events_integrity detecta enlaces reescritos (columna↔payload + forma
  de la cadena), no solo la auto-consistencia hash.
- TipoFactura R5 para rectificativas de simplificadas (L2).
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.config import settings
from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.services.billing.registro_facturacion import default_sistema_informatico
from app.services.billing.sif_events import (
    EVENT_ARRANQUE,
    EVENT_RESTAURACION,
    record_event,
    verify_events_integrity,
)
from app.services.billing.verifactu_chain import append_verifactu_record


def test_settings_declara_verifactu_sif():
    """El .env ahora surte efecto: los campos existen en Settings y el
    SistemaInformatico los lee de ahí (no placeholders silenciosos)."""
    assert settings.VERIFACTU_SIF_NIF  # declarado (default placeholder)
    sif = default_sistema_informatico()
    assert sif.nif == settings.VERIFACTU_SIF_NIF
    assert sif.version == settings.VERIFACTU_SIF_VERSION
    assert hasattr(settings, "VERIFACTU_SIF_DIRECCION")
    assert hasattr(settings, "VERIFACTU_SIF_LUGAR")


@pytest.mark.asyncio
class TestPayloadEventos:
    async def test_payload_lleva_los_8_campos(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        ev = await record_event(db, tenant_id=tenant.id, tipo_evento=EVENT_ARRANQUE, detalle="boot")
        await db.commit()
        p = ev.payload_canonico
        for campo in (
            "NIFProductor=",
            "IDSistemaInformatico=",
            "Version=",
            "NumeroInstalacion=",
            "NIFObligado=",
            "TipoEvento=",
            "HuellaAnterior=",
            "FechaHoraHusoGenRegistro=",
        ):
            assert campo in p, f"falta {campo} en el payload"
        assert "NIFObligado=B12345678" in p  # NIF del tenant seed
        assert f"NIFProductor={settings.VERIFACTU_SIF_NIF}" in p

    async def test_huso_madrid_en_payload(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        ev = await record_event(db, tenant_id=tenant.id, tipo_evento=EVENT_ARRANQUE)
        fh = ev.payload_canonico.split("FechaHoraHusoGenRegistro=")[1].split("&")[0]
        # Europe/Madrid: +01:00 (invierno) o +02:00 (verano) — nunca Z/+00:00.
        assert fh.endswith("+01:00") or fh.endswith("+02:00")

    async def test_restauracion_es_valido_y_encadena(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        e1 = await record_event(db, tenant_id=tenant.id, tipo_evento=EVENT_ARRANQUE)
        e2 = await record_event(db, tenant_id=tenant.id, tipo_evento=EVENT_RESTAURACION, detalle="backup X")
        await db.commit()
        assert e2.huella_anterior == e1.huella
        ok, n = await verify_events_integrity(db, tenant.id)
        assert ok is True and n == 2


@pytest.mark.asyncio
class TestIntegridadEnlace:
    async def test_detecta_enlace_reescrito(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        await record_event(db, tenant_id=tenant.id, tipo_evento=EVENT_ARRANQUE)
        ev2 = await record_event(db, tenant_id=tenant.id, tipo_evento=EVENT_RESTAURACION)
        await db.commit()

        # Tamper (posible en SQLite, sin triggers WORM): reescribe el enlace de
        # la COLUMNA dejando payload y huella intactos — antes pasaba el check.
        ev2.huella_anterior = "0" * 64
        await db.commit()

        ok, _ = await verify_events_integrity(db, tenant.id)
        assert ok is False


def _inv(tenant_id, client_id, *, number, itype="issued", simplified=False, rectifies=None):
    inv = Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number,
        date=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
        amount_base=Decimal("100.00"),
        tax_amount=Decimal("21.00"),
        amount_total=Decimal("121.00"),
        status="pending",
        invoice_type=itype,
        is_simplified=simplified,
    )
    if rectifies is not None:
        inv.rectifies_invoice_id = rectifies
    return inv


@pytest.mark.asyncio
class TestR5:
    async def _setup(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Cliente")
        db.add(client)
        await db.flush()
        return tenant, client

    async def test_rectificativa_de_simplificada_es_r5(self, db, seed_tenant_and_user):
        tenant, client = await self._setup(db, seed_tenant_and_user)
        simp = _inv(tenant.id, client.id, number="T-9", simplified=True)
        db.add(simp)
        await db.flush()
        rect = _inv(tenant.id, client.id, number="R-9", itype="rectificativa", rectifies=simp.id)
        db.add(rect)
        await db.flush()

        rec = await append_verifactu_record(db, invoice=rect, nif_emisor="B12345678")
        await db.commit()
        assert "TipoFactura=R5" in rec.payload_canonico

    async def test_rectificativa_de_completa_sigue_r1(self, db, seed_tenant_and_user):
        tenant, client = await self._setup(db, seed_tenant_and_user)
        full = _inv(tenant.id, client.id, number="A-9", simplified=False)
        db.add(full)
        await db.flush()
        rect = _inv(tenant.id, client.id, number="R-10", itype="rectificativa", rectifies=full.id)
        db.add(rect)
        await db.flush()

        rec = await append_verifactu_record(db, invoice=rect, nif_emisor="B12345678")
        await db.commit()
        assert "TipoFactura=R1" in rec.payload_canonico
        assert "TipoFactura=R5" not in rec.payload_canonico
