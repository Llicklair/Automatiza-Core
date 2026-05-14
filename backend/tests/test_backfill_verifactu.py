"""Tests del backfill histórico Verifactu (A.5)."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.db.models.billing import Invoice, VerifactuRecord
from app.db.models.crm import Client
from app.services.billing.backfill_verifactu import (
    backfill_tenant_verifactu_chain,
    list_tenants_pending_backfill,
)
from app.services.billing.verifactu_chain import (
    append_verifactu_record,
    verify_chain_integrity,
)


def _mk_invoice(tenant_id, client_id, *, invoice_number: str, importe: str, day: int) -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=invoice_number,
        date=datetime(2026, 1, day, 10, 0, tzinfo=timezone.utc),
        amount_base=Decimal(importe),
        tax_amount=Decimal("0.00"),
        amount_total=Decimal(importe),
        invoice_type="issued",
    )


@pytest.mark.asyncio
class TestBackfillVerifactu:
    async def _seed(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Acme SL")
        db.add(client)
        await db.flush()
        return tenant, client

    async def test_backfill_vacio_si_no_hay_facturas(self, db, seed_tenant_and_user):
        tenant, _ = await self._seed(db, seed_tenant_and_user)

        result = await backfill_tenant_verifactu_chain(
            db, tenant_id=tenant.id, nif_emisor="B99999999",
        )
        await db.commit()

        assert result.invoices_total == 0
        assert result.backfilled == 0
        assert result.is_empty

    async def test_backfill_genera_cadena_cronologica(self, db, seed_tenant_and_user):
        tenant, client = await self._seed(db, seed_tenant_and_user)

        # Tres facturas históricas en orden cronológico inverso al inserto.
        inv_c = _mk_invoice(tenant.id, client.id, invoice_number="A2026-0003", importe="300.00", day=15)
        inv_a = _mk_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe="100.00", day=5)
        inv_b = _mk_invoice(tenant.id, client.id, invoice_number="A2026-0002", importe="200.00", day=10)
        db.add_all([inv_c, inv_a, inv_b])
        await db.flush()

        result = await backfill_tenant_verifactu_chain(
            db, tenant_id=tenant.id, nif_emisor="B99999999",
        )
        await db.commit()

        assert result.invoices_total == 3
        assert result.already_chained == 0
        assert result.backfilled == 3

        # Cadena íntegra y en orden cronológico.
        ok, count = await verify_chain_integrity(db, tenant.id)
        assert ok is True
        assert count == 3

    async def test_backfill_es_idempotente(self, db, seed_tenant_and_user):
        tenant, client = await self._seed(db, seed_tenant_and_user)

        inv = _mk_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe="121.00", day=5)
        db.add(inv)
        await db.flush()

        # Primera corrida.
        result1 = await backfill_tenant_verifactu_chain(
            db, tenant_id=tenant.id, nif_emisor="B99999999",
        )
        await db.commit()
        assert result1.backfilled == 1

        # Segunda corrida: no debe duplicar.
        result2 = await backfill_tenant_verifactu_chain(
            db, tenant_id=tenant.id, nif_emisor="B99999999",
        )
        await db.commit()
        assert result2.backfilled == 0
        assert result2.already_chained == 1

    async def test_backfill_marca_is_backfilled_true(self, db, seed_tenant_and_user):
        tenant, client = await self._seed(db, seed_tenant_and_user)
        inv = _mk_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe="121.00", day=5)
        db.add(inv)
        await db.flush()

        await backfill_tenant_verifactu_chain(
            db, tenant_id=tenant.id, nif_emisor="B99999999",
        )
        await db.commit()

        from sqlalchemy import select
        row = (await db.execute(select(VerifactuRecord))).scalar_one()
        assert row.is_backfilled is True
        assert row.backfilled_at is not None

    async def test_backfill_continua_cadena_existente(self, db, seed_tenant_and_user):
        """Si ya hay registros en tiempo real, el backfill encadena detrás."""
        tenant, client = await self._seed(db, seed_tenant_and_user)

        # Primero una factura emitida normalmente.
        inv_real = _mk_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe="100.00", day=20)
        db.add(inv_real)
        await db.flush()
        await append_verifactu_record(db, invoice=inv_real, nif_emisor="B99999999")
        await db.commit()

        # Después se importa una factura histórica (sin Verifactu).
        inv_hist = _mk_invoice(tenant.id, client.id, invoice_number="A2026-0002", importe="200.00", day=25)
        db.add(inv_hist)
        await db.flush()

        result = await backfill_tenant_verifactu_chain(
            db, tenant_id=tenant.id, nif_emisor="B99999999",
        )
        await db.commit()

        assert result.invoices_total == 2
        assert result.already_chained == 1
        assert result.backfilled == 1

        # La cadena debe seguir íntegra.
        ok, count = await verify_chain_integrity(db, tenant.id)
        assert ok is True
        assert count == 2

    async def test_list_tenants_pending_backfill_detecta(self, db, seed_tenant_and_user):
        tenant, client = await self._seed(db, seed_tenant_and_user)

        inv = _mk_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe="121.00", day=5)
        db.add(inv)
        await db.flush()
        await db.commit()

        pending = await list_tenants_pending_backfill(db)
        assert tenant.id in pending

    async def test_list_tenants_pending_backfill_vacio_tras_backfill(
        self, db, seed_tenant_and_user
    ):
        tenant, client = await self._seed(db, seed_tenant_and_user)
        inv = _mk_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe="121.00", day=5)
        db.add(inv)
        await db.flush()

        await backfill_tenant_verifactu_chain(
            db, tenant_id=tenant.id, nif_emisor="B99999999",
        )
        await db.commit()

        pending = await list_tenants_pending_backfill(db)
        assert tenant.id not in pending
