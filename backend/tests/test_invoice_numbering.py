"""Tests para `next_invoice_number` — numeración correlativa (FAC.NUM)."""
import uuid

import pytest
from app.services.billing.numbering import next_invoice_number


@pytest.mark.asyncio
class TestNextInvoiceNumber:
    async def test_primera_factura_emite_0001(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user
        number = await next_invoice_number(db, tenant.id, series="A", year=2026)
        await db.commit()
        assert number == "A2026-0001"

    async def test_correlativa_sin_gaps(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user
        numbers = []
        for _ in range(5):
            numbers.append(await next_invoice_number(db, tenant.id, series="A", year=2026))
        await db.commit()
        assert numbers == [
            "A2026-0001",
            "A2026-0002",
            "A2026-0003",
            "A2026-0004",
            "A2026-0005",
        ]

    async def test_series_distintas_son_independientes(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user
        a = await next_invoice_number(db, tenant.id, series="A", year=2026)
        b = await next_invoice_number(db, tenant.id, series="B", year=2026)
        a2 = await next_invoice_number(db, tenant.id, series="A", year=2026)
        await db.commit()
        assert a == "A2026-0001"
        assert b == "B2026-0001"
        assert a2 == "A2026-0002"

    async def test_anos_distintos_son_independientes(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user
        n_2026 = await next_invoice_number(db, tenant.id, series="A", year=2026)
        n_2027 = await next_invoice_number(db, tenant.id, series="A", year=2027)
        await db.commit()
        assert n_2026 == "A2026-0001"
        assert n_2027 == "A2027-0001"

    async def test_tenants_distintos_son_independientes(
        self, db, seed_tenant_and_user, seed_second_tenant_and_user
    ):
        t1, _u1, _tok1 = seed_tenant_and_user
        t2, _u2, _tok2 = seed_second_tenant_and_user
        n1 = await next_invoice_number(db, t1.id, series="A", year=2026)
        n2 = await next_invoice_number(db, t2.id, series="A", year=2026)
        await db.commit()
        assert n1 == "A2026-0001"
        assert n2 == "A2026-0001"  # series independiente por tenant

    async def test_no_emite_uuid(self, db, seed_tenant_and_user):
        # Regresión del bug histórico "IA-XXXXXXXX" (UUID).
        tenant, _user, _token = seed_tenant_and_user
        number = await next_invoice_number(db, tenant.id, series="A", year=2026)
        await db.commit()
        assert not number.startswith("IA-")
        # No debe contener un hex UUID
        try:
            uuid.UUID(number.split("-")[-1])
            pytest.fail("invoice_number contiene UUID, debería ser correlativo")
        except ValueError:
            pass  # correcto: el sufijo es secuencial, no UUID
