"""La ruta de envío a VeriFactu ya NO finge 'enviado'.

Antes, /invoices/{id}/verifactu-send llamaba a una simulación que ponía
verifactu_status='sent' sin enviar nada a la AEAT. Ahora usa el pipeline real,
INACTIVO por defecto: con el modo no_remission (default) o sin registro en la
cadena, NO se marca enviado. Solo un acuse real 'Correcto' marca 'sent'.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models.billing import Invoice, VerifactuRecord
from app.db.models.crm import Client
from app.services.billing.verifactu_submit import submit_invoice_to_verifactu

pytestmark = pytest.mark.asyncio


async def _invoice(db, tenant_id, *, number: str) -> Invoice:
    client = Client(tenant_id=tenant_id, nif="B12345678", name="Acme SL")
    db.add(client)
    await db.flush()
    inv = Invoice(
        tenant_id=tenant_id,
        client_id=client.id,
        invoice_number=number,
        date=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
        amount_base=Decimal("100.00"),
        tax_amount=Decimal("21.00"),
        amount_total=Decimal("121.00"),
    )
    db.add(inv)
    await db.flush()
    return inv


async def test_no_remission_no_marca_enviado(db, seed_tenant_and_user):
    """Modo por defecto (no_remission): no-op, NO finge 'enviado'."""
    tenant, _u, _t = seed_tenant_and_user
    inv = await _invoice(db, tenant.id, number="A2026-0001")
    db.add(VerifactuRecord(
        tenant_id=tenant.id,
        invoice_id=inv.id,
        huella="a" * 64,
        payload_canonico="{}",
        nif_emisor="B12345678",
        serie_factura="A",
        numero_factura="A2026-0001",
        fecha_emision=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
        importe_total=Decimal("121.00"),
    ))
    await db.commit()

    res = await submit_invoice_to_verifactu(db, inv.id, tenant.id, confirmed=False)

    assert res["remitted"] is False
    refreshed = (await db.execute(select(Invoice).where(Invoice.id == inv.id))).scalar_one()
    assert refreshed.verifactu_status != "sent", "no debe fingir envío en modo no_remission"


async def test_sin_registro_en_cadena_no_envia(db, seed_tenant_and_user):
    """Factura sin registro VeriFactu: no se envía nada y no se marca enviado."""
    tenant, _u, _t = seed_tenant_and_user
    inv = await _invoice(db, tenant.id, number="A2026-0002")
    await db.commit()

    res = await submit_invoice_to_verifactu(db, inv.id, tenant.id, confirmed=False)

    assert res["remitted"] is False
    refreshed = (await db.execute(select(Invoice).where(Invoice.id == inv.id))).scalar_one()
    assert refreshed.verifactu_status != "sent"


async def test_factura_inexistente_lanza_valueerror(db, seed_tenant_and_user):
    import uuid

    tenant, _u, _t = seed_tenant_and_user
    with pytest.raises(ValueError):
        await submit_invoice_to_verifactu(db, uuid.uuid4(), tenant.id, confirmed=False)
