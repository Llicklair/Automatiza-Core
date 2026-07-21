"""Cierres B1/B2/B3 del re-audit adversarial (2026-07-21).

- B1: la tool del agente `update_invoice_status` EXPIDE vía el chokepoint →
  un "marca la factura como enviada" sobre un borrador encadena el registro
  VeriFactu (antes mutaba status + commit directo: expedición sin registro).
- B2: la misma tool NO puede anular una factura con registro (rectificativa).
- B3: `create_rectificativa` respeta el 0% (no coerciona a 21%) y hereda
  `exencion_causa` de la original.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.agents.billing._invoice_write_tools import _update_invoice_status_async
from app.db.models.billing import Invoice, InvoiceLine, VerifactuRecord
from app.db.models.crm import Client
from app.services.billing.commands import create_rectificativa
from app.services.billing.verifactu_chain import ensure_verifactu_on_expedition
from app.services.billing.verifactu_mode import set_mode


async def _seed(db, tenant_id, *, number, status="draft", tax="21.00", exencion=None):
    cli = Client(tenant_id=tenant_id, name="Cliente Agente SL", nif="B33333333")
    db.add(cli)
    await db.flush()
    inv = Invoice(
        tenant_id=tenant_id,
        client_id=cli.id,
        invoice_number=number,
        date=datetime(2026, 5, 10, tzinfo=UTC),
        amount_base=Decimal("100.00"),
        tax_amount=Decimal(tax),
        amount_total=Decimal("100.00") + Decimal(tax),
        invoice_type="issued",
        status=status,
        exencion_causa=exencion,
    )
    db.add(inv)
    await db.flush()
    db.add(
        InvoiceLine(
            invoice_id=inv.id,
            description="Servicio",
            quantity=1,
            unit_price=100.0,
            discount_percentage=0,
            tax_percentage=float(Decimal(tax)),
            total=float(Decimal("100.00") + Decimal(tax)),
        )
    )
    await db.flush()
    return inv


async def _records(db, invoice_id):
    res = await db.execute(select(VerifactuRecord).where(VerifactuRecord.invoice_id == invoice_id))
    return res.scalars().all()


@pytest.mark.asyncio
class TestAgenteExpide:
    async def test_b1_expedir_desde_agente_encadena(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        inv = await _seed(db, tenant.id, number="AG-1", status="draft")
        await db.commit()

        out = await _update_invoice_status_async(str(tenant.id), str(inv.id), "sent")

        assert not out.startswith("Error"), out
        assert len(await _records(db, inv.id)) == 1  # expedición → registro

    async def test_b2_anular_con_registro_bloqueado_desde_agente(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        inv = await _seed(db, tenant.id, number="AG-2", status="pending")
        rec = await ensure_verifactu_on_expedition(db, inv)
        assert rec is not None
        await db.commit()

        out = await _update_invoice_status_async(str(tenant.id), str(inv.id), "cancelled")

        assert out.startswith("Error")
        assert "rectificativa" in out
        await db.refresh(inv)
        assert inv.status == "pending"  # sin cambios

    async def test_transicion_invalida_sigue_dando_error_claro(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        inv = await _seed(db, tenant.id, number="AG-3", status="cancelled")
        await db.commit()

        out = await _update_invoice_status_async(str(tenant.id), str(inv.id), "paid")
        assert out.startswith("Error")


@pytest.mark.asyncio
class TestRectificativaExenta:
    async def test_b3_rectificativa_de_exenta_conserva_0_y_causa(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        original = await _seed(db, tenant.id, number="EX-1", status="paid", tax="0.00", exencion="E1")
        await db.commit()

        rect = await create_rectificativa(original.id, "anulación de venta exenta", tenant.id, db)

        assert rect.exencion_causa == "E1"
        lines = (await db.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == rect.id))).scalars().all()
        assert lines, "la rectificativa debe tener líneas"
        for ln in lines:
            # El bug coercionaba Decimal('0.00') → 21% (falsy) e inventaba IVA.
            assert float(ln.tax_percentage) == 0.0
        assert Decimal(str(rect.tax_amount)) == Decimal("0.00")

    async def test_rectificativa_normal_sigue_al_21(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        original = await _seed(db, tenant.id, number="EX-2", status="paid", tax="21.00")
        await db.commit()

        rect = await create_rectificativa(original.id, "anulación", tenant.id, db)

        lines = (await db.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == rect.id))).scalars().all()
        for ln in lines:
            assert float(ln.tax_percentage) == 21.0
