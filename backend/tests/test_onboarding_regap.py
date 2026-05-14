"""Tests del wizard REGAP (PRES.REG)."""
import pytest

from app.services.onboarding.regap import (
    get_regap_status,
    mark_power_granted,
    reset_regap,
    start_identification,
    verify_regap_consulta,
)


@pytest.mark.asyncio
class TestRegapWizard:
    async def test_status_inicial_es_not_started(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user

        record = await get_regap_status(db, tenant_id=tenant.id)
        await db.commit()

        assert record.status == "not_started"
        assert record.auth_method is None
        assert record.verified_at is None

    async def test_idempotente(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user

        r1 = await get_regap_status(db, tenant_id=tenant.id)
        r2 = await get_regap_status(db, tenant_id=tenant.id)
        await db.commit()

        assert r1.id == r2.id  # Devuelve el mismo registro

    async def test_start_clave_va_a_identifying(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user

        record = await start_identification(
            db, tenant_id=tenant.id, auth_method="clave_pin",
        )
        await db.commit()

        assert record.status == "identifying"
        assert record.auth_method == "clave_pin"

    async def test_start_cert_fnmt_va_a_cert_pending(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user

        record = await start_identification(
            db, tenant_id=tenant.id, auth_method="cert_fnmt",
        )
        await db.commit()

        assert record.status == "cert_pending"
        assert record.auth_method == "cert_fnmt"

    async def test_grant_solo_desde_identifying_o_cert_pending(
        self, db, seed_tenant_and_user
    ):
        tenant, _user, _token = seed_tenant_and_user

        # No se puede saltar a grant desde not_started.
        with pytest.raises(ValueError):
            await mark_power_granted(db, tenant_id=tenant.id)

    async def test_flow_completo_clave_pin(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user

        # 1. start
        r = await start_identification(
            db, tenant_id=tenant.id, auth_method="clave_pin",
        )
        assert r.status == "identifying"

        # 2. grant
        r = await mark_power_granted(db, tenant_id=tenant.id)
        assert r.status == "power_granted"

        # 3. verify (mock devuelve VIGENTE)
        r = await verify_regap_consulta(
            db, tenant_id=tenant.id, nif_cliente="B12345678",
        )
        await db.commit()

        assert r.status == "verified"
        assert r.verified_at is not None
        assert r.verify_payload is not None
        assert "B12345678" in r.verify_payload

    async def test_verify_solo_desde_power_granted(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user

        with pytest.raises(ValueError):
            await verify_regap_consulta(
                db, tenant_id=tenant.id, nif_cliente="B12345678",
            )

    async def test_reset_vuelve_a_not_started(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user

        await start_identification(
            db, tenant_id=tenant.id, auth_method="cert_fnmt",
        )
        r = await reset_regap(db, tenant_id=tenant.id)
        await db.commit()

        assert r.status == "not_started"
        assert r.auth_method is None
        assert r.verified_at is None
        assert r.rejected_reason is None
