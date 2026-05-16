"""Tests de idempotencia de tools críticas (QA.IDM).

Objetivo: garantizar que reintentar una tool tras crash o timeout NO
duplica registros ni rompe invariantes (cadena Verifactu, numeración
correlativa, append-only de audit).

Casos cubiertos:
- `append_verifactu_record` reintento sobre misma factura → 1 registro,
  cadena íntegra.
- Numeración correlativa: dos llamadas concurrentes obtienen números
  distintos (NO idempotente por diseño — cada commit consume número).
- Flujo combinado: secuencia create_invoice (futuro) + verifactu se
  recupera de un fallo intermedio.
"""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.db.models.billing import Invoice, VerifactuRecord
from app.db.models.crm import Client
from app.services.billing.numbering import next_invoice_number
from app.services.billing.verifactu_chain import (
    append_verifactu_record,
    verify_chain_integrity,
)
from sqlalchemy import func, select


def _invoice(tenant_id, client_id, *, num: str, importe: str = "121.00") -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=num,
        date=datetime(2026, 1, 15, 10, 0, tzinfo=UTC),
        amount_base=Decimal(importe),
        tax_amount=Decimal("0.00"),
        amount_total=Decimal(importe),
        invoice_type="issued",
    )


@pytest.mark.asyncio
class TestVerifactuIdempotency:
    async def _seed(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Acme SL")
        db.add(client)
        await db.flush()
        return tenant, client

    async def test_doble_append_no_duplica(self, db, seed_tenant_and_user):
        tenant, client = await self._seed(db, seed_tenant_and_user)
        inv = _invoice(tenant.id, client.id, num="A2026-0001")
        db.add(inv)
        await db.flush()

        r1 = await append_verifactu_record(db, invoice=inv, nif_emisor="B99999999")
        r2 = await append_verifactu_record(db, invoice=inv, nif_emisor="B99999999")
        await db.commit()

        assert r1.id == r2.id  # devuelve el mismo registro

        count = await db.execute(
            select(func.count(VerifactuRecord.id)).where(
                VerifactuRecord.invoice_id == inv.id,
            )
        )
        assert count.scalar_one() == 1

    async def test_cadena_intacta_tras_reintento(self, db, seed_tenant_and_user):
        tenant, client = await self._seed(db, seed_tenant_and_user)

        # Tres facturas en orden. La 2ª se intenta 3 veces (simulando crash+reintento).
        for i, num in enumerate(["A2026-0001", "A2026-0002", "A2026-0003"]):
            inv = _invoice(tenant.id, client.id, num=num, importe=f"{100 + i}.00")
            db.add(inv)
            await db.flush()
            await append_verifactu_record(db, invoice=inv, nif_emisor="B99999999")
            if num == "A2026-0002":
                # Reintento doble — debe ser idempotente.
                await append_verifactu_record(db, invoice=inv, nif_emisor="B99999999")
                await append_verifactu_record(db, invoice=inv, nif_emisor="B99999999")

        await db.commit()

        # Cadena íntegra y con exactamente 3 registros.
        ok, count = await verify_chain_integrity(db, tenant.id)
        assert ok is True
        assert count == 3

    async def test_reintento_con_nif_distinto_no_corrompe(
        self, db, seed_tenant_and_user
    ):
        """Si el reintento llega con un NIF emisor distinto, debe ignorarlo
        y devolver el registro original (el primer commit fijó el hash).
        Evita que un segundo agente "corrija" datos a posteriori."""
        tenant, client = await self._seed(db, seed_tenant_and_user)
        inv = _invoice(tenant.id, client.id, num="A2026-0001")
        db.add(inv)
        await db.flush()

        r1 = await append_verifactu_record(db, invoice=inv, nif_emisor="B99999999")
        r2 = await append_verifactu_record(db, invoice=inv, nif_emisor="B00000000")
        await db.commit()

        assert r1.id == r2.id
        assert r2.nif_emisor == "B99999999"  # se conserva el primero

    async def test_payload_y_huella_son_inmutables(self, db, seed_tenant_and_user):
        tenant, client = await self._seed(db, seed_tenant_and_user)
        inv = _invoice(tenant.id, client.id, num="A2026-0001")
        db.add(inv)
        await db.flush()

        r1 = await append_verifactu_record(db, invoice=inv, nif_emisor="B99999999")
        first_payload = r1.payload_canonico
        first_huella = r1.huella

        r2 = await append_verifactu_record(db, invoice=inv, nif_emisor="B99999999")
        await db.commit()

        assert r2.payload_canonico == first_payload
        assert r2.huella == first_huella


@pytest.mark.asyncio
class TestNumberingNonIdempotent:
    """Numeración correlativa NO es idempotente — cada llamada consume.

    Esta es la decisión consensuada: el caller (create_invoice) es quien
    debe gatear con su propia idempotencia (UNIQUE en invoice_number o
    external_id). El servicio de numeración solo garantiza unicidad.
    """

    async def test_dos_llamadas_consecutivas_dan_numeros_distintos(
        self, db, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user

        n1 = await next_invoice_number(db, tenant_id=tenant.id, series="A", year=2026)
        n2 = await next_invoice_number(db, tenant_id=tenant.id, series="A", year=2026)
        await db.commit()

        assert n1 != n2
        # Mismo prefijo "A2026-" y diferencia de 1 en el sufijo.
        prefix1, suffix1 = n1.rsplit("-", 1)
        prefix2, suffix2 = n2.rsplit("-", 1)
        assert prefix1 == prefix2
        assert int(suffix2) == int(suffix1) + 1

    async def test_aislamiento_entre_tenants(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        from uuid import uuid4
        other = uuid4()

        n1 = await next_invoice_number(db, tenant_id=tenant.id, series="A", year=2026)
        n2 = await next_invoice_number(db, tenant_id=other, series="A", year=2026)
        await db.commit()

        # Tenants distintos pueden tener el mismo número (sus series son independientes).
        suffix1 = n1.rsplit("-", 1)[1]
        suffix2 = n2.rsplit("-", 1)[1]
        # Ambos deben empezar desde 0001 porque las series no comparten contador.
        assert suffix1 == "0001"
        assert suffix2 == "0001"


@pytest.mark.asyncio
class TestCombinedFlowIdempotency:
    async def test_reintento_completo_secuencia(self, db, seed_tenant_and_user):
        """Simula el patrón típico de retry: error transitorio entre
        next_invoice_number y append_verifactu_record.

        Decisión: numbering NO es idempotente. La idempotencia debe
        venir del UNIQUE en `invoice_number` por (tenant, serie, año).
        Si el caller hace COMMIT entre número y verifactu, el reintento
        debe usar el número ya asignado a la factura existente, no pedir
        uno nuevo.
        """
        tenant, _u, _t = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Acme")
        db.add(client)
        await db.flush()

        # 1er intento: número + factura, fallo justo antes de verifactu.
        num = await next_invoice_number(db, tenant_id=tenant.id, series="A", year=2026)
        inv = _invoice(tenant.id, client.id, num=num)
        db.add(inv)
        await db.flush()
        await db.commit()

        # Reintento: en lugar de pedir número nuevo, recupera la factura
        # incompleta y completa solo el paso pendiente (verifactu).
        existing_q = await db.execute(
            select(Invoice).where(Invoice.invoice_number == num, Invoice.tenant_id == tenant.id)
        )
        existing = existing_q.scalar_one()
        await append_verifactu_record(db, invoice=existing, nif_emisor="B99999999")
        await db.commit()

        # Estado coherente: 1 factura, 1 verifactu record, cadena íntegra.
        inv_count = (await db.execute(
            select(func.count(Invoice.id)).where(
                Invoice.tenant_id == tenant.id, Invoice.invoice_number == num,
            )
        )).scalar_one()
        assert inv_count == 1

        vf_count = (await db.execute(
            select(func.count(VerifactuRecord.id)).where(
                VerifactuRecord.tenant_id == tenant.id,
            )
        )).scalar_one()
        assert vf_count == 1

        ok, _ = await verify_chain_integrity(db, tenant.id)
        assert ok is True
