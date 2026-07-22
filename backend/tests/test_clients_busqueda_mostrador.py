"""Buscador único del mostrador (tintorería T3): un solo campo busca por
nombre, NIF, teléfono o email en /clients?q=."""

import pytest

from app.db.models.crm import Client
from app.services.sales.queries import list_clients


async def _seed(db, tenant_id):
    db.add_all(
        [
            Client(tenant_id=tenant_id, name="Ana Pérez", nif="12345678Z", phone="600111222"),
            Client(tenant_id=tenant_id, name="Bruno López", nif="87654321X", phone="699888777"),
            Client(tenant_id=tenant_id, name="Carla Ruiz", email="carla@mail.com"),
        ]
    )
    await db.flush()


@pytest.mark.asyncio
async def test_busca_por_nombre_nif_telefono_email(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    await _seed(db, tenant.id)

    assert [c.name for c in await list_clients(db, tenant.id, q="ana")] == ["Ana Pérez"]
    assert [c.name for c in await list_clients(db, tenant.id, q="87654321")] == ["Bruno López"]
    assert [c.name for c in await list_clients(db, tenant.id, q="600111")] == ["Ana Pérez"]
    assert [c.name for c in await list_clients(db, tenant.id, q="carla@")] == ["Carla Ruiz"]


@pytest.mark.asyncio
async def test_sin_q_devuelve_todos(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    await _seed(db, tenant.id)
    assert len(await list_clients(db, tenant.id)) == 3
    assert len(await list_clients(db, tenant.id, q="  ")) == 3  # espacios = sin filtro
