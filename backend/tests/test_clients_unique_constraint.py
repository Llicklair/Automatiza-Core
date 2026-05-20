"""Tests para la constraint UNIQUE(tenant_id, nif) en clients.

Cubre el bug latente arreglado en iter 2026-05-19: el upsert de billing
podía crear duplicados bajo race condition. Ahora la BD lo previene.
"""

from uuid import uuid4

import pytest
from app.db.models.models import Client, Tenant
from sqlalchemy.exc import IntegrityError


@pytest.fixture
async def _tenant(db):
    t = Tenant(
        id=uuid4(),
        name="Test Unique",
        nif=f"U{uuid4().int % 10**8:08d}",
    )
    db.add(t)
    await db.commit()
    return t


@pytest.mark.asyncio
class TestClientUniqueConstraint:
    async def test_no_se_pueden_insertar_dos_clients_mismo_nif_mismo_tenant(self, db, _tenant):
        nif = "B12345678"
        c1 = Client(tenant_id=_tenant.id, nif=nif, name="Acme S.L.")
        db.add(c1)
        await db.commit()

        c2 = Client(tenant_id=_tenant.id, nif=nif, name="Acme Duplicado")
        db.add(c2)
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()

    async def test_mismo_nif_distinto_tenant_OK(self, db, _tenant):
        """Aislamiento multi-tenant: el mismo NIF puede aparecer en tenants distintos."""
        other = Tenant(
            id=uuid4(),
            name="Other Tenant",
            nif=f"O{uuid4().int % 10**8:08d}",
        )
        db.add(other)
        await db.commit()

        nif = "C99999999"
        db.add(Client(tenant_id=_tenant.id, nif=nif, name="Mi Acme"))
        db.add(Client(tenant_id=other.id, nif=nif, name="Su Acme"))
        await db.commit()  # no debe lanzar

    async def test_nif_None_permite_multiples(self, db, _tenant):
        """Particulares sin NIF se pueden registrar múltiples veces."""
        db.add(Client(tenant_id=_tenant.id, nif=None, name="Particular 1"))
        db.add(Client(tenant_id=_tenant.id, nif=None, name="Particular 2"))
        await db.commit()  # no debe lanzar

    async def test_nif_vacio_permite_multiples(self, db, _tenant):
        """nif='' tratado como ausente — particulares ocasionales sin NIF."""
        db.add(Client(tenant_id=_tenant.id, nif="", name="Particular A"))
        db.add(Client(tenant_id=_tenant.id, nif="", name="Particular B"))
        await db.commit()  # no debe lanzar
