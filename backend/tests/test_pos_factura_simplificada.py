"""Puente TPV → factura simplificada (F2). Fase 2 del POS.

Una sesión de TPV cerrada genera una Invoice simplificada (is_simplified,
invoice_type 'issued', cobrada) con un cliente mostrador genérico y su registro
VeriFactu con TipoFactura F2. Idempotente: una sesión se factura una sola vez.
"""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.db.models.billing import Invoice, VerifactuRecord
from app.db.models.crm import Client
from app.db.models.pos import PosSession, PosSessionLine
from app.services.billing.verifactu_mode import set_mode
from app.services.sales.pos import (
    WALK_IN_CLIENT_NAME,
    generar_factura_simplificada,
)


async def _closed_session(db, tenant, user, *, total=Decimal("121.00")):
    session = PosSession(
        tenant_id=tenant.id,
        user_id=user.id,
        status="closed",
        payment_method="cash",
        amount_subtotal=Decimal("100.00"),
        tax_amount=Decimal("21.00"),
        amount_total=total,
    )
    db.add(session)
    await db.flush()
    db.add(
        PosSessionLine(
            session_id=session.id,
            tenant_id=tenant.id,
            description="Lavado y planchado",
            quantity=1,
            unit_price=Decimal("100.00"),
            tax_percentage=Decimal("21.00"),
            total=Decimal("121.00"),
        )
    )
    await db.commit()
    return session


@pytest.mark.asyncio
class TestFacturaSimplificada:
    async def test_sesion_cerrada_emite_factura_f2(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        session = await _closed_session(db, tenant, user)

        invoice = await generar_factura_simplificada(db, tenant.id, session.id)

        assert invoice.is_simplified is True
        assert invoice.invoice_type == "issued"
        assert invoice.status == "paid"
        assert invoice.amount_total == Decimal("121.00")
        assert len(invoice.lines) == 1
        # Cliente mostrador genérico, sin NIF (consumidor final).
        assert invoice.client.name == WALK_IN_CLIENT_NAME
        assert not invoice.client.nif

        # La sesión queda enlazada a su factura.
        await db.refresh(session)
        assert session.invoice_id == invoice.id

        # Registro VeriFactu con TipoFactura F2.
        rec = await db.execute(select(VerifactuRecord).where(VerifactuRecord.invoice_id == invoice.id))
        record = rec.scalar_one()
        assert "TipoFactura=F2" in record.payload_canonico

        # QR Verifactu derivable del registro (para pintarlo en el ticket).
        from app.services.billing.queries import load_verifactu_qr

        qr = await load_verifactu_qr(invoice.id, db)
        assert qr is not None
        assert qr["huella"] == record.huella
        # El QR encoda la URL de cotejo de la AEAT (ValidarQR + los 4 parametros).
        assert "ValidarQR" in qr["verify_url"]
        assert "nif=" in qr["verify_url"] and "numserie=" in qr["verify_url"]

    async def test_idempotente_no_duplica_factura(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        session = await _closed_session(db, tenant, user)

        inv1 = await generar_factura_simplificada(db, tenant.id, session.id)
        inv2 = await generar_factura_simplificada(db, tenant.id, session.id)

        assert inv1.id == inv2.id
        count = await db.execute(select(func.count(Invoice.id)).where(Invoice.tenant_id == tenant.id))
        assert count.scalar() == 1
        recs = await db.execute(select(VerifactuRecord).where(VerifactuRecord.invoice_id == inv1.id))
        assert len(recs.scalars().all()) == 1

    async def test_sesion_abierta_no_se_factura(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        session = PosSession(tenant_id=tenant.id, user_id=user.id, status="open")
        db.add(session)
        await db.commit()

        with pytest.raises(ValueError, match="cerrada"):
            await generar_factura_simplificada(db, tenant.id, session.id)

    async def test_cliente_mostrador_se_reutiliza(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        s1 = await _closed_session(db, tenant, user)
        s2 = await _closed_session(db, tenant, user)

        await generar_factura_simplificada(db, tenant.id, s1.id)
        await generar_factura_simplificada(db, tenant.id, s2.id)

        count = await db.execute(
            select(func.count(Client.id)).where(Client.tenant_id == tenant.id, Client.name == WALK_IN_CLIENT_NAME)
        )
        assert count.scalar() == 1

    async def test_importe_supera_limite_no_se_emite_como_simplificada(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        session = await _closed_session(db, tenant, user, total=Decimal("3500.00"))

        with pytest.raises(ValueError, match="límite"):
            await generar_factura_simplificada(db, tenant.id, session.id)
