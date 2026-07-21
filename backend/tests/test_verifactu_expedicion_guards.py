"""P1 — guardas de expedición Verifactu: toda factura EMITIDA queda encadenada.

Cierra los hallazgos del audit 2026-07-21:
  - `ensure_verifactu_on_expedition`: recibidas/demo/borradores NO encadenan;
    emitidas expedidas SÍ (guardas centralizadas, antes solo en update_status).
  - Conciliación bancaria draft→paid encadena (bypass del chokepoint cerrado).
  - Anulación bloqueada si hay registro Verifactu (política = rectificativa,
    igual que delete_invoice).
  - bulk_import rechaza facturas emitidas con VeriFactu activo (bypass cerrado);
    en no_remission siguen importándose como históricas sin cadena (diseño).
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models.billing import Invoice, VerifactuRecord
from app.db.models.crm import Client
from app.db.models.models import BankTransaction
from app.services.banking.service import auto_reconcile, reconcile_transaction
from app.services.billing.commands import update_status
from app.services.billing.verifactu_chain import ensure_verifactu_on_expedition
from app.services.billing.verifactu_mode import set_mode
from app.services.migration.bulk_import import import_invoices_rows


def _invoice(tenant_id, client_id, *, number, status="pending", itype="issued", total="121.00", demo=False):
    total_d = Decimal(total)
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number,
        date=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
        amount_base=total_d - Decimal("21.00"),
        tax_amount=Decimal("21.00"),
        amount_total=total_d,
        status=status,
        invoice_type=itype,
        is_demo=demo,
    )


async def _record_count(db, invoice_id) -> int:
    res = await db.execute(select(VerifactuRecord).where(VerifactuRecord.invoice_id == invoice_id))
    return len(res.scalars().all())


@pytest.mark.asyncio
class TestGuardasHelper:
    async def _setup(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Cliente")
        db.add(client)
        await db.flush()
        return tenant, user, client

    async def test_recibida_no_encadena(self, db, seed_tenant_and_user):
        tenant, _u, client = await self._setup(db, seed_tenant_and_user)
        inv = _invoice(tenant.id, client.id, number="PROV-77", itype="received", status="paid")
        db.add(inv)
        await db.flush()

        assert await ensure_verifactu_on_expedition(db, inv) is None
        assert await _record_count(db, inv.id) == 0

    async def test_demo_no_encadena(self, db, seed_tenant_and_user):
        tenant, _u, client = await self._setup(db, seed_tenant_and_user)
        inv = _invoice(tenant.id, client.id, number="D-1", status="sent", demo=True)
        db.add(inv)
        await db.flush()

        assert await ensure_verifactu_on_expedition(db, inv) is None
        assert await _record_count(db, inv.id) == 0

    async def test_borrador_no_encadena_hasta_expedirse(self, db, seed_tenant_and_user):
        tenant, _u, client = await self._setup(db, seed_tenant_and_user)
        inv = _invoice(tenant.id, client.id, number="A-10", status="draft")
        db.add(inv)
        await db.flush()

        # Borrador: sin registro (la expedición es el hecho fiscal).
        assert await ensure_verifactu_on_expedition(db, inv) is None
        assert await _record_count(db, inv.id) == 0

        # Expedida: encadena.
        inv.status = "pending"
        rec = await ensure_verifactu_on_expedition(db, inv)
        assert rec is not None
        assert await _record_count(db, inv.id) == 1


@pytest.mark.asyncio
class TestBankingExpide:
    async def _setup(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Cliente Banco")
        db.add(client)
        await db.flush()
        return tenant, user, client

    async def test_conciliacion_manual_de_borrador_encadena(self, db, seed_tenant_and_user):
        tenant, user, client = await self._setup(db, seed_tenant_and_user)
        inv = _invoice(tenant.id, client.id, number="A-100", status="draft")
        tx = BankTransaction(
            tenant_id=tenant.id,
            date=datetime(2026, 5, 15, tzinfo=UTC),
            amount=Decimal("121.00"),
            description="Transferencia Cliente Banco",
            status="unreconciled",
        )
        db.add_all([inv, tx])
        await db.flush()

        await reconcile_transaction(db, tenant.id, user.id, tx.id, str(inv.id))

        assert inv.status == "paid"
        # El bypass draft→paid ya no deja la factura expedida sin registro.
        assert await _record_count(db, inv.id) == 1

    async def test_auto_reconcile_de_borrador_encadena(self, db, seed_tenant_and_user):
        tenant, user, client = await self._setup(db, seed_tenant_and_user)
        inv = _invoice(tenant.id, client.id, number="A-200", status="draft", total="500.00")
        tx = BankTransaction(
            tenant_id=tenant.id,
            date=datetime(2026, 5, 16, tzinfo=UTC),
            amount=Decimal("500.00"),
            description="Pago factura A-200 Cliente Banco",
            status="unreconciled",
        )
        db.add_all([inv, tx])
        await db.flush()
        await db.commit()

        res = await auto_reconcile(db, tenant.id, user.id)

        assert res["matched"] == 1
        assert await _record_count(db, inv.id) == 1


@pytest.mark.asyncio
class TestAnulacionBloqueada:
    async def _setup(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Cliente")
        db.add(client)
        await db.flush()
        return tenant, user, client

    async def test_anular_con_registro_exige_rectificativa(self, db, seed_tenant_and_user):
        tenant, _u, client = await self._setup(db, seed_tenant_and_user)
        inv = _invoice(tenant.id, client.id, number="A-300", status="pending")
        db.add(inv)
        await db.flush()
        rec = await ensure_verifactu_on_expedition(db, inv)
        assert rec is not None
        await db.commit()

        with pytest.raises(ValueError, match="rectificativa"):
            await update_status(inv.id, tenant.id, "cancelled", db)

    async def test_anular_borrador_sin_registro_ok(self, db, seed_tenant_and_user):
        tenant, _u, client = await self._setup(db, seed_tenant_and_user)
        inv = _invoice(tenant.id, client.id, number="A-301", status="draft")
        db.add(inv)
        await db.flush()
        await db.commit()

        out = await update_status(inv.id, tenant.id, "cancelled", db)
        assert out.status == "cancelled"
        assert await _record_count(db, inv.id) == 0


@pytest.mark.asyncio
class TestBulkImportGuard:
    async def _client(self, db, tenant_id):
        client = Client(tenant_id=tenant_id, nif="B99999999", name="Cliente Migrado")
        db.add(client)
        await db.flush()

    def _row(self, *, numero, tipo):
        return {
            "numero": numero,
            "tipo": tipo,
            "nif": "B99999999",
            "cliente": "Cliente Migrado",
            "fecha": "2024-03-10",
            "total": "121.00",
            "estado": "paid",
        }

    async def test_voluntary_rechaza_emitidas(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        await self._client(db, tenant.id)

        res = await import_invoices_rows([self._row(numero="H-1", tipo="issued")], tenant.id, db)

        assert res.created == 0
        assert res.skipped == 1
        assert any("bypass" in e["reason"] for e in res.errors)
        dup = await db.execute(select(Invoice).where(Invoice.invoice_number == "H-1"))
        assert dup.scalar_one_or_none() is None

    async def test_voluntary_permite_recibidas(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        await self._client(db, tenant.id)

        res = await import_invoices_rows([self._row(numero="P-1", tipo="received")], tenant.id, db)

        assert res.created == 1
        inv = (await db.execute(select(Invoice).where(Invoice.invoice_number == "P-1"))).scalar_one()
        assert await _record_count(db, inv.id) == 0

    async def test_no_remission_importa_historicas_sin_cadena(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user  # default: no_remission
        await self._client(db, tenant.id)

        res = await import_invoices_rows([self._row(numero="H-2", tipo="issued")], tenant.id, db)

        assert res.created == 1
        inv = (await db.execute(select(Invoice).where(Invoice.invoice_number == "H-2"))).scalar_one()
        assert await _record_count(db, inv.id) == 0
