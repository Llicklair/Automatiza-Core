"""Tests del modo de remisión Verifactu (FAC.MODE)."""
from uuid import uuid4

import pytest

from app.services.billing.verifactu_mode import (
    DEFAULT_MODE,
    get_config,
    get_mode,
    set_mode,
    should_remit,
    to_dict,
)


@pytest.mark.asyncio
class TestVerifactuMode:
    async def test_default_es_no_remission(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        mode = await get_mode(db, tenant_id=tenant.id)
        assert mode == "no_remission"
        assert DEFAULT_MODE == "no_remission"

    async def test_get_config_idempotente(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        r1 = await get_config(db, tenant_id=tenant.id)
        r2 = await get_config(db, tenant_id=tenant.id)
        await db.commit()

        assert r1.id == r2.id

    async def test_set_mode_voluntary(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user

        record = await set_mode(
            db, tenant_id=tenant.id, mode="voluntary", updated_by=user.id,
        )
        await db.commit()

        assert record.mode == "voluntary"
        assert record.updated_by == user.id

    async def test_set_mode_alterna(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        await set_mode(db, tenant_id=tenant.id, mode="no_remission")
        await db.commit()

        mode = await get_mode(db, tenant_id=tenant.id)
        assert mode == "no_remission"

    async def test_set_mode_rechaza_invalido(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        with pytest.raises(ValueError, match="Modo inválido"):
            await set_mode(db, tenant_id=tenant.id, mode="weird")  # type: ignore

    async def test_should_remit_segun_modo(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        assert await should_remit(db, tenant_id=tenant.id) is False

        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        await db.commit()
        assert await should_remit(db, tenant_id=tenant.id) is True

    async def test_aislamiento_entre_tenants(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        other = uuid4()

        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        await db.commit()

        assert await get_mode(db, tenant_id=tenant.id) == "voluntary"
        assert await get_mode(db, tenant_id=other) == "no_remission"

    async def test_to_dict_marca_is_default(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        record = await get_config(db, tenant_id=tenant.id)
        out = to_dict(record)
        assert out["mode"] == "no_remission"
        assert out["is_default"] is True

        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        record = await get_config(db, tenant_id=tenant.id)
        out = to_dict(record)
        assert out["mode"] == "voluntary"
        assert out["is_default"] is False
