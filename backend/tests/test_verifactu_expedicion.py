"""Regresión doble-uso (RD 1007/2023 Art. 8, art. 201 bis LGT).

Toda factura EMITIDA con Verifactu en modo 'voluntary' debe generar su registro
encadenado. El agujero cerrado aquí: las facturas nacidas como BORRADOR
(quote→factura, aprobación de workflow, recurrentes del scheduler, reanudación
del orquestador) se expiden vía ``update_status``, que NO encadenaba el registro
→ factura emitida sin registro (doble uso). Y un tenant en 'voluntary' sin NIF
se saltaba el registro con un simple warning, emitiendo igualmente.
"""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.db.models.billing import Invoice, VerifactuRecord
from app.db.models.crm import Client
from app.services.billing.commands import update_status
from app.services.billing.verifactu_chain import maybe_append_verifactu_record
from app.services.billing.verifactu_mode import set_mode
from sqlalchemy import select


def _draft_issued(tenant_id, client_id, *, number: str) -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number,
        date=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
        amount_base=Decimal("100.00"),
        tax_amount=Decimal("21.00"),
        amount_total=Decimal("121.00"),
        status="draft",
        invoice_type="issued",
    )


async def _record_for(db, invoice_id):
    res = await db.execute(select(VerifactuRecord).where(VerifactuRecord.invoice_id == invoice_id))
    return res.scalar_one_or_none()


@pytest.mark.asyncio
class TestExpedicionGeneraRegistro:
    async def _setup_voluntary(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Acme SL")
        db.add(client)
        await db.flush()
        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        await db.commit()
        return tenant, client

    async def test_borrador_al_expedirse_genera_registro(self, db, seed_tenant_and_user):
        tenant, client = await self._setup_voluntary(db, seed_tenant_and_user)
        inv = _draft_issued(tenant.id, client.id, number="A2026-0001")
        db.add(inv)
        await db.commit()

        # Un borrador aún no se ha expedido → todavía no debe tener registro.
        assert await _record_for(db, inv.id) is None

        # Expedición: draft → sent. Aquí debe encadenarse el registro.
        await update_status(inv.id, tenant.id, "sent", db)

        rec = await _record_for(db, inv.id)
        assert rec is not None
        assert len(rec.huella) == 64
        assert rec.nif_emisor == tenant.nif

    async def test_expedicion_idempotente_no_duplica(self, db, seed_tenant_and_user):
        tenant, client = await self._setup_voluntary(db, seed_tenant_and_user)
        inv = _draft_issued(tenant.id, client.id, number="A2026-0002")
        db.add(inv)
        await db.commit()

        await update_status(inv.id, tenant.id, "sent", db)
        await update_status(inv.id, tenant.id, "paid", db)

        recs = await db.execute(select(VerifactuRecord).where(VerifactuRecord.invoice_id == inv.id))
        assert len(recs.scalars().all()) == 1

    async def test_borrador_cancelado_no_genera_registro(self, db, seed_tenant_and_user):
        tenant, client = await self._setup_voluntary(db, seed_tenant_and_user)
        inv = _draft_issued(tenant.id, client.id, number="A2026-0003")
        db.add(inv)
        await db.commit()

        # draft → cancelled: nunca se expidió → no debe registrar.
        await update_status(inv.id, tenant.id, "cancelled", db)
        assert await _record_for(db, inv.id) is None


@pytest.mark.asyncio
class TestNifObligatorioEnVoluntary:
    async def test_sin_nif_bloquea_emision_en_voluntary(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        tenant.nif = ""  # emisor sin NIF fiscal configurado (columna NOT NULL: "" no None)
        await db.flush()
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Acme SL")
        db.add(client)
        await db.flush()
        await set_mode(db, tenant_id=tenant.id, mode="voluntary")

        inv = _draft_issued(tenant.id, client.id, number="A2026-0004")
        db.add(inv)
        await db.flush()

        # Antes: warning + None (factura emitida sin registro). Ahora: se bloquea.
        with pytest.raises(ValueError, match="NIF"):
            await maybe_append_verifactu_record(db, invoice=inv)
