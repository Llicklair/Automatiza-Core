"""Facturas simplificadas (ticket TPV) → registro Verifactu con TipoFactura F2.

Lista L2 (RD 1007/2023 + Orden HAC/1177/2024): una factura simplificada se
registra con TipoFactura=F2, no F1. Es la base de conformidad del TPV: sin esto
el ticket de caja no puede emitir un registro VeriFactu correcto.
"""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.services.billing.verifactu_chain import append_verifactu_record


def _invoice(tenant_id, client_id, *, number: str, simplified: bool) -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number,
        date=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
        amount_base=Decimal("100.00"),
        tax_amount=Decimal("21.00"),
        amount_total=Decimal("121.00"),
        status="pending",
        invoice_type="issued",
        is_simplified=simplified,
    )


@pytest.mark.asyncio
class TestRegistroF2:
    async def _setup(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Cliente Mostrador")
        db.add(client)
        await db.flush()
        return tenant, client

    async def test_simplificada_genera_tipofactura_f2(self, db, seed_tenant_and_user):
        tenant, client = await self._setup(db, seed_tenant_and_user)
        inv = _invoice(tenant.id, client.id, number="T2026-0001", simplified=True)
        db.add(inv)
        await db.flush()

        rec = await append_verifactu_record(db, invoice=inv, nif_emisor="B12345678")
        await db.commit()

        # La huella se calcula sobre el payload canónico → TipoFactura debe ser F2.
        assert "TipoFactura=F2" in rec.payload_canonico
        assert "TipoFactura=F1" not in rec.payload_canonico
        assert len(rec.huella) == 64

    async def test_completa_sigue_siendo_f1(self, db, seed_tenant_and_user):
        tenant, client = await self._setup(db, seed_tenant_and_user)
        inv = _invoice(tenant.id, client.id, number="A2026-0001", simplified=False)
        db.add(inv)
        await db.flush()

        rec = await append_verifactu_record(db, invoice=inv, nif_emisor="B12345678")
        await db.commit()

        assert "TipoFactura=F1" in rec.payload_canonico
