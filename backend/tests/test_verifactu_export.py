"""Exportación / conservación de registros de un periodo (RD 1007/2023 art. 8.2.c)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models.billing import Invoice, SifEvent
from app.db.models.crm import Client
from app.services.billing.sif_events import EVENT_ARRANQUE, EVENT_EXPORTACION, record_event
from app.services.billing.verifactu_chain import append_verifactu_record
from app.services.billing.verifactu_export import export_periodo

_DESDE = datetime(2000, 1, 1, tzinfo=UTC)
_HASTA = datetime(2100, 1, 1, tzinfo=UTC)


@pytest.mark.asyncio
class TestExportPeriodo:
    async def test_recoge_registros_eventos_y_genera_eventos_exportacion(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Cliente")
        db.add(client)
        await db.flush()
        inv = Invoice(
            tenant_id=tenant.id,
            client_id=client.id,
            invoice_number="A2026-0001",
            date=datetime(2026, 5, 14, tzinfo=UTC),
            amount_base=Decimal("100.00"),
            tax_amount=Decimal("21.00"),
            amount_total=Decimal("121.00"),
        )
        db.add(inv)
        await db.flush()
        await append_verifactu_record(db, invoice=inv, nif_emisor="B12345678")
        await record_event(db, tenant_id=tenant.id, tipo_evento=EVENT_ARRANQUE)
        await db.flush()

        result = await export_periodo(db, tenant_id=tenant.id, desde=_DESDE, hasta=_HASTA)
        await db.commit()

        assert result["counts"]["facturas"] == 1
        assert result["counts"]["eventos"] == 1  # el ARRANQUE (los EXPORTACION se registran después)
        assert result["registros_facturacion"][0]["numero_factura"] == "A2026-0001"
        assert "TipoFactura=F1" in result["registros_facturacion"][0]["payload_canonico"]

        # Se registraron los dos eventos de exportación (facturas + eventos).
        exp = (
            (
                await db.execute(
                    select(SifEvent).where(
                        SifEvent.tenant_id == tenant.id,
                        SifEvent.tipo_evento == EVENT_EXPORTACION,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(exp) == 2

    async def test_periodo_vacio_devuelve_cero_pero_registra_export(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        result = await export_periodo(db, tenant_id=tenant.id, desde=_DESDE, hasta=_HASTA)
        await db.commit()
        assert result["counts"] == {"facturas": 0, "eventos": 0}
        exp = (
            (
                await db.execute(
                    select(SifEvent).where(
                        SifEvent.tenant_id == tenant.id,
                        SifEvent.tipo_evento == EVENT_EXPORTACION,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(exp) == 2

    async def test_export_xml_contiene_registroalta_del_periodo(self, db, seed_tenant_and_user):
        from xml.etree.ElementTree import fromstring

        from app.services.billing.verifactu_export import export_periodo_xml

        tenant, _u, _t = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Cliente")
        db.add(client)
        await db.flush()
        inv = Invoice(
            tenant_id=tenant.id,
            client_id=client.id,
            invoice_number="A2026-0055",
            date=datetime(2026, 5, 14, tzinfo=UTC),
            amount_base=Decimal("100.00"),
            tax_amount=Decimal("21.00"),
            amount_total=Decimal("121.00"),
        )
        db.add(inv)
        await db.flush()
        await append_verifactu_record(db, invoice=inv, nif_emisor="B12345678")
        await db.flush()

        xml = await export_periodo_xml(db, tenant_id=tenant.id, desde=_DESDE, hasta=_HASTA)
        await db.commit()

        assert xml.startswith("<?xml")
        assert "A2026-0055" in xml  # NumSerieFactura en el RegistroAlta
        root = fromstring(xml)
        assert root.tag == "ExportacionRegistrosFacturacion"
        assert len(list(root)) == 1  # un RegistroAlta en el periodo
