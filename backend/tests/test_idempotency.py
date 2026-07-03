"""Tests de idempotencia de la numeración correlativa (QA.IDM).

La numeración correlativa NO es idempotente por diseño: cada llamada a
`next_invoice_number` consume un número. El caller es quien gatea con su
propia idempotencia (UNIQUE en `invoice_number`). El servicio de numeración
solo garantiza unicidad y aislamiento entre tenants.
"""
import pytest
from app.services.billing.numbering import next_invoice_number


@pytest.mark.asyncio
class TestNumberingNonIdempotent:
    """Numeración correlativa NO es idempotente — cada llamada consume.

    Esta es la decisión consensuada: el caller es quien debe gatear con su
    propia idempotencia (UNIQUE en invoice_number o external_id). El servicio
    de numeración solo garantiza unicidad.
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
