"""Tests del wizard onboarding focado (UI.ONB)."""
import pytest

from app.services.onboarding.wizard import (
    get_state,
    reset,
    set_step,
    skip_to_end,
    to_dict,
)


@pytest.mark.asyncio
class TestWizard:
    async def test_estado_inicial_todo_falso(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        record = await get_state(db, tenant_id=tenant.id)
        await db.commit()

        assert record.step_company is False
        assert record.step_cert is False
        assert record.step_data is False
        assert record.step_use_case is False
        assert record.completed_at is None
        assert record.skipped_at is None

    async def test_set_step_marca_un_paso(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        record = await set_step(db, tenant_id=tenant.id, step="company", value=True)
        await db.commit()

        assert record.step_company is True
        assert record.step_cert is False

    async def test_completar_los_4_setea_completed_at(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        for step in ("company", "cert", "data", "use_case"):
            record = await set_step(db, tenant_id=tenant.id, step=step, value=True)
        await db.commit()

        assert record.completed_at is not None

    async def test_completed_at_no_se_resetea_al_revertir(
        self, db, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user

        # Completar todos
        for step in ("company", "cert", "data", "use_case"):
            await set_step(db, tenant_id=tenant.id, step=step, value=True)
        await db.commit()

        # Revertir uno: completed_at se mantiene (decisión: la primera vez completado
        # ya pasó; no queremos perder el timestamp original).
        record = await set_step(db, tenant_id=tenant.id, step="data", value=False)
        await db.commit()

        assert record.completed_at is not None  # mantiene primer timestamp

    async def test_skip_marca_skipped_at(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        record = await skip_to_end(db, tenant_id=tenant.id)
        await db.commit()

        assert record.skipped_at is not None
        assert record.completed_at is None  # skipped != completed

    async def test_skip_idempotente(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        r1 = await skip_to_end(db, tenant_id=tenant.id)
        first_at = r1.skipped_at
        r2 = await skip_to_end(db, tenant_id=tenant.id)
        await db.commit()

        assert r2.skipped_at == first_at  # no se sobrescribe

    async def test_set_step_invalido(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        with pytest.raises(ValueError, match="Paso desconocido"):
            await set_step(db, tenant_id=tenant.id, step="invalid", value=True)  # type: ignore

    async def test_reset_borra_todo(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        await set_step(db, tenant_id=tenant.id, step="company", value=True)
        await skip_to_end(db, tenant_id=tenant.id)
        record = await reset(db, tenant_id=tenant.id)
        await db.commit()

        assert record.step_company is False
        assert record.skipped_at is None
        assert record.completed_at is None

    async def test_to_dict_marca_is_dismissed(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        record = await get_state(db, tenant_id=tenant.id)
        out = to_dict(record)
        assert out["is_dismissed"] is False

        await skip_to_end(db, tenant_id=tenant.id)
        out2 = to_dict(record)
        assert out2["is_dismissed"] is True
