"""Tests para la cadena hash Verifactu (FAC.HASH) — RD 1007/2023 Art. 8."""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.db.models.billing import Invoice, VerifactuRecord
from app.db.models.crm import Client
from app.services.billing.verifactu_chain import (
    append_verifactu_record,
    build_payload_alta,
    build_payload_anulacion,
    compute_huella,
    maybe_append_verifactu_record,
    verify_chain_integrity,
)
from sqlalchemy import select


def _make_invoice(tenant_id, client_id, *, invoice_number: str, importe: Decimal) -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=invoice_number,
        date=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
        amount_base=importe,
        tax_amount=Decimal("0.00"),
        amount_total=importe,
    )


def _payload_alta(**over):
    base = dict(
        id_emisor="B12345678",
        num_serie_factura="A2026-0001",
        fecha_expedicion="14-05-2026",
        tipo_factura="F1",
        cuota_total=Decimal("21.00"),
        importe_total=Decimal("121.00"),
        huella_anterior=None,
        fecha_hora_gen="2026-05-14T10:00:00+00:00",
    )
    base.update(over)
    return build_payload_alta(**base)


class TestVectorOficialAEAT:
    """Conformidad con el vector de prueba publicado por la AEAT en
    «Detalle de las especificaciones técnicas para la generación de la huella».
    Reproducir su hash exacto demuestra que el formato canónico es el oficial.
    """

    EJEMPLO = (
        "IDEmisorFactura=89890001K&NumSerieFactura=12345678/G33"
        "&FechaExpedicionFactura=01-01-2024&TipoFactura=F1"
        "&CuotaTotal=12.35&ImporteTotal=123.45&Huella="
        "&FechaHoraHusoGenRegistro=2024-01-01T19:20:30+01:00"
    )
    HUELLA = "3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60"

    def test_cadena_canonica_coincide_con_el_ejemplo(self):
        payload = build_payload_alta(
            id_emisor="89890001K",
            num_serie_factura="12345678/G33",
            fecha_expedicion="01-01-2024",
            tipo_factura="F1",
            cuota_total=Decimal("12.35"),
            importe_total=Decimal("123.45"),
            huella_anterior=None,
            fecha_hora_gen="2024-01-01T19:20:30+01:00",
        )
        assert payload == self.EJEMPLO

    def test_huella_coincide_con_el_vector_oficial(self):
        assert compute_huella(self.EJEMPLO) == self.HUELLA


class TestBuildPayloadAlta:
    def test_formato_determinista(self):
        assert _payload_alta() == _payload_alta()
        p = _payload_alta()
        assert "IDEmisorFactura=B12345678" in p
        assert "NumSerieFactura=A2026-0001" in p
        assert "ImporteTotal=121.00" in p
        assert "CuotaTotal=21.00" in p

    def test_orden_oficial_de_campos(self):
        p = _payload_alta()
        campos = [kv.split("=", 1)[0] for kv in p.split("&")]
        assert campos == [
            "IDEmisorFactura", "NumSerieFactura", "FechaExpedicionFactura",
            "TipoFactura", "CuotaTotal", "ImporteTotal", "Huella",
            "FechaHoraHusoGenRegistro",
        ]

    def test_huella_anterior_vacia_si_none(self):
        assert "&Huella=&" in _payload_alta(huella_anterior=None)

    def test_huella_anterior_encadenada(self):
        assert "&Huella=ABCDEF&" in _payload_alta(huella_anterior="ABCDEF")

    def test_importe_2_decimales_insensible_a_ceros(self):
        a = _payload_alta(importe_total=Decimal("121"))
        b = _payload_alta(importe_total=Decimal("121.00"))
        c = _payload_alta(importe_total=Decimal("121.000"))
        assert a == b == c


class TestBuildPayloadAnulacion:
    def test_subconjunto_de_campos_anulacion(self):
        p = build_payload_anulacion(
            id_emisor="B12345678",
            num_serie_factura="A2026-0001",
            fecha_expedicion="14-05-2026",
            huella_anterior=None,
            fecha_hora_gen="2026-05-14T10:00:00+00:00",
        )
        campos = [kv.split("=", 1)[0] for kv in p.split("&")]
        assert campos == [
            "IDEmisorFacturaAnulada", "NumSerieFacturaAnulada",
            "FechaExpedicionFacturaAnulada", "Huella", "FechaHoraHusoGenRegistro",
        ]


class TestComputeHuella:
    def test_es_sha256_hex_mayusculas(self):
        h = compute_huella("payload-prueba")
        assert len(h) == 64
        # La AEAT exige el hex en MAYÚSCULAS.
        assert all(c in "0123456789ABCDEF" for c in h)

    def test_determinista(self):
        assert compute_huella("misma-cadena") == compute_huella("misma-cadena")

    def test_cambio_detectable(self):
        assert compute_huella("a") != compute_huella("a ")


@pytest.mark.asyncio
class TestAppendVerifactuRecord:
    async def _setup_tenant_and_client(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Acme SL")
        db.add(client)
        await db.flush()
        return tenant, client

    async def test_primer_registro_huella_anterior_es_none(
        self, db, seed_tenant_and_user
    ):
        tenant, client = await self._setup_tenant_and_client(db, seed_tenant_and_user)
        invoice = _make_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe=Decimal("121.00"))
        db.add(invoice)
        await db.flush()

        record = await append_verifactu_record(db, invoice=invoice, nif_emisor="B99999999")
        await db.commit()

        assert record.huella_anterior is None
        assert len(record.huella) == 64
        assert record.nif_emisor == "B99999999"
        assert record.numero_factura == "A2026-0001"

    async def test_segundo_registro_encadena_al_primero(
        self, db, seed_tenant_and_user
    ):
        tenant, client = await self._setup_tenant_and_client(db, seed_tenant_and_user)
        inv1 = _make_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe=Decimal("100.00"))
        inv2 = _make_invoice(tenant.id, client.id, invoice_number="A2026-0002", importe=Decimal("200.00"))
        db.add_all([inv1, inv2])
        await db.flush()

        r1 = await append_verifactu_record(db, invoice=inv1, nif_emisor="B99999999")
        await db.flush()
        r2 = await append_verifactu_record(db, invoice=inv2, nif_emisor="B99999999")
        await db.commit()

        assert r1.huella_anterior is None
        assert r2.huella_anterior == r1.huella
        assert r2.huella != r1.huella

    async def test_idempotencia_no_duplica_para_misma_factura(
        self, db, seed_tenant_and_user
    ):
        tenant, client = await self._setup_tenant_and_client(db, seed_tenant_and_user)
        inv = _make_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe=Decimal("121.00"))
        db.add(inv)
        await db.flush()

        r1 = await append_verifactu_record(db, invoice=inv, nif_emisor="B99999999")
        await db.flush()
        r2 = await append_verifactu_record(db, invoice=inv, nif_emisor="B99999999")
        await db.commit()

        assert r1.id == r2.id

    async def test_cadenas_independientes_por_tenant(
        self, db, seed_tenant_and_user, seed_second_tenant_and_user
    ):
        t1, _u1, _tok1 = seed_tenant_and_user
        t2, _u2, _tok2 = seed_second_tenant_and_user
        c1 = Client(tenant_id=t1.id, nif="B11111111", name="T1 Client")
        c2 = Client(tenant_id=t2.id, nif="B22222222", name="T2 Client")
        db.add_all([c1, c2])
        await db.flush()

        inv1 = _make_invoice(t1.id, c1.id, invoice_number="A2026-0001", importe=Decimal("100.00"))
        inv2 = _make_invoice(t2.id, c2.id, invoice_number="A2026-0001", importe=Decimal("200.00"))
        db.add_all([inv1, inv2])
        await db.flush()

        r1 = await append_verifactu_record(db, invoice=inv1, nif_emisor="B11111111")
        r2 = await append_verifactu_record(db, invoice=inv2, nif_emisor="B22222222")
        await db.commit()

        # Ambos son primer registro de su tenant → huella_anterior None.
        assert r1.huella_anterior is None
        assert r2.huella_anterior is None
        # Huellas distintas porque payloads distintos.
        assert r1.huella != r2.huella

    async def test_verify_chain_integrity_ok(self, db, seed_tenant_and_user):
        tenant, client = await self._setup_tenant_and_client(db, seed_tenant_and_user)
        invs = [
            _make_invoice(tenant.id, client.id, invoice_number=f"A2026-{i:04d}", importe=Decimal(f"{i*10}.00"))
            for i in range(1, 6)
        ]
        db.add_all(invs)
        await db.flush()
        for inv in invs:
            await append_verifactu_record(db, invoice=inv, nif_emisor="B99999999")
            await db.flush()
        await db.commit()

        ok, count = await verify_chain_integrity(db, tenant.id)
        assert ok is True
        assert count == 5

    async def test_verify_chain_integrity_detecta_manipulacion(
        self, db, seed_tenant_and_user
    ):
        # Manipulación: cambiar huella manualmente debe romper la verificación.
        tenant, client = await self._setup_tenant_and_client(db, seed_tenant_and_user)
        inv = _make_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe=Decimal("121.00"))
        db.add(inv)
        await db.flush()
        record = await append_verifactu_record(db, invoice=inv, nif_emisor="B99999999")
        await db.flush()

        # Simulamos manipulación: cambiar huella sin recomputar
        record.huella = "0" * 64
        await db.flush()

        ok, count = await verify_chain_integrity(db, tenant.id)
        assert ok is False
        assert count == 1


@pytest.mark.asyncio
class TestMaybeAppendVerifactuRecord:
    """Regresión: ambos paths de creación de factura (servicio y agente)
    DEBEN encadenar el registro Verifactu cuando el modo del tenant es
    'voluntary'. Sin esto el PDF sale sin QR (RD 1007/2023 Art. 8 FAC.QR).
    """

    async def test_modo_no_remission_no_crea_registro(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Acme SL")
        db.add(client)
        await db.flush()
        invoice = _make_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe=Decimal("121.00"))
        db.add(invoice)
        await db.flush()

        # Sin VerifactuConfig el tenant arranca en 'no_remission' → no debe encadenar.
        result = await maybe_append_verifactu_record(db, invoice=invoice)
        assert result is None
        chain = await db.execute(
            select(VerifactuRecord).where(VerifactuRecord.invoice_id == invoice.id)
        )
        assert chain.scalar_one_or_none() is None

    async def test_modo_voluntary_si_crea_registro(self, db, seed_tenant_and_user):
        from app.services.billing.verifactu_mode import set_mode

        tenant, _user, _token = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Acme SL")
        db.add(client)
        await db.flush()
        invoice = _make_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe=Decimal("121.00"))
        db.add(invoice)
        await db.flush()

        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        result = await maybe_append_verifactu_record(db, invoice=invoice)
        await db.commit()

        assert result is not None
        assert len(result.huella) == 64
        # nif_emisor sale del Tenant, no de un parámetro: cubre el bug original
        # (cualquiera de los dos paths de creación olvidaba pasarlo).
        assert result.nif_emisor == tenant.nif
