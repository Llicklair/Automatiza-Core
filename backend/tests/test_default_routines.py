"""Rutinas de oficio: seed idempotente y wiring con el catálogo de eventos."""

import pytest
from sqlalchemy import select

from app.db.models.workflows import Workflow
from app.services import events_catalog as ev
from app.services.workflow.default_routines import DEFAULT_ROUTINES, seed_default_routines

pytestmark = pytest.mark.asyncio


async def test_seed_crea_todas_las_rutinas(db, seed_tenant_and_user):
    tenant, user, _token = seed_tenant_and_user
    created = await seed_default_routines(db, tenant.id, user.id)
    await db.commit()
    assert sorted(created) == sorted(DEFAULT_ROUTINES.keys())

    res = await db.execute(select(Workflow).where(Workflow.tenant_id == tenant.id))
    workflows = res.scalars().all()
    assert len(workflows) == len(DEFAULT_ROUTINES)
    for wf in workflows:
        assert wf.trigger_type == "event_based"
        assert wf.is_active
        assert wf.action_config.get("routine_key") in DEFAULT_ROUTINES
        assert wf.action_config.get("instruction")


async def test_seed_es_idempotente(db, seed_tenant_and_user):
    tenant, user, _token = seed_tenant_and_user
    await seed_default_routines(db, tenant.id, user.id)
    await db.commit()
    again = await seed_default_routines(db, tenant.id, user.id)
    assert again == []


async def test_eventos_de_rutinas_estan_en_catalogo():
    for key, spec in DEFAULT_ROUTINES.items():
        for event in spec["events"]:
            assert event in ev.ALL_EVENTS, f"Rutina {key} escucha evento fuera de catálogo"


async def test_registro_siembra_rutinas(db):
    """El alta de tenant (register) deja las rutinas sembradas."""
    from app.services.auth._schemas import TenantCreate, UserCreate
    from app.services.auth.service import register

    payload = UserCreate(
        email="owner@nueva-pyme.com",
        password="SuperSegura123!",
        full_name="Dueño Nuevo",
        tenant=TenantCreate(name="Nueva Pyme SL", nif="B98765432"),
    )
    user = await register(payload, db)
    res = await db.execute(select(Workflow).where(Workflow.tenant_id == user.tenant_id))
    assert len(res.scalars().all()) == len(DEFAULT_ROUTINES)
