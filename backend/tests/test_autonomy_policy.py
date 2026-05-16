"""Tests del servicio de autonomía por dominio (SEC.AUT)."""
import pytest
from app.services.autonomy import (
    DEFAULTS,
    KNOWN_DOMAINS,
    check_autonomy,
    default_mode,
    list_policies,
    reset_policy,
    set_policy,
)


class TestDefaults:
    def test_banking_write_es_manual(self):
        assert default_mode("banking_write") == "MANUAL"

    def test_accounting_es_confirm(self):
        assert default_mode("accounting") == "CONFIRM"

    def test_marketing_es_confirm(self):
        assert default_mode("marketing") == "CONFIRM"

    def test_recruitment_es_confirm(self):
        assert default_mode("recruitment") == "CONFIRM"

    def test_resto_es_auto(self):
        assert default_mode("crm") == "AUTO"
        assert default_mode("rag") == "AUTO"
        assert default_mode("banking_read") == "AUTO"


@pytest.mark.asyncio
class TestServiceCRUD:
    async def test_check_autonomy_devuelve_default_sin_fila(
        self, db, seed_tenant_and_user
    ):
        tenant, _user, _token = seed_tenant_and_user

        mode = await check_autonomy(db, tenant_id=tenant.id, domain="banking_write")
        assert mode == "MANUAL"

        mode = await check_autonomy(db, tenant_id=tenant.id, domain="crm")
        assert mode == "AUTO"

    async def test_set_policy_persiste(self, db, seed_tenant_and_user):
        tenant, user, _token = seed_tenant_and_user

        await set_policy(
            db, tenant_id=tenant.id, domain="crm", mode="MANUAL", updated_by=user.id,
        )
        await db.commit()

        mode = await check_autonomy(db, tenant_id=tenant.id, domain="crm")
        assert mode == "MANUAL"

    async def test_set_policy_upsert(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user

        await set_policy(db, tenant_id=tenant.id, domain="crm", mode="MANUAL")
        await set_policy(db, tenant_id=tenant.id, domain="crm", mode="AUTO")
        await db.commit()

        mode = await check_autonomy(db, tenant_id=tenant.id, domain="crm")
        assert mode == "AUTO"

    async def test_set_policy_rechaza_dominio_desconocido(
        self, db, seed_tenant_and_user
    ):
        tenant, _user, _token = seed_tenant_and_user

        with pytest.raises(ValueError, match="Dominio desconocido"):
            await set_policy(db, tenant_id=tenant.id, domain="bogus", mode="AUTO")

    async def test_set_policy_rechaza_modo_invalido(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user

        with pytest.raises(ValueError, match="Modo inválido"):
            await set_policy(db, tenant_id=tenant.id, domain="crm", mode="WHATEVER")  # type: ignore

    async def test_reset_vuelve_al_default(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user

        await set_policy(db, tenant_id=tenant.id, domain="accounting", mode="AUTO")
        await db.commit()
        assert await check_autonomy(db, tenant_id=tenant.id, domain="accounting") == "AUTO"

        await reset_policy(db, tenant_id=tenant.id, domain="accounting")
        await db.commit()
        # Sin fila → default del dominio
        assert await check_autonomy(db, tenant_id=tenant.id, domain="accounting") == "CONFIRM"

    async def test_list_policies_marca_is_default(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user

        await set_policy(db, tenant_id=tenant.id, domain="crm", mode="MANUAL")
        await db.commit()

        policies = await list_policies(db, tenant_id=tenant.id)

        # Todos los dominios conocidos están presentes
        assert set(policies.keys()) == KNOWN_DOMAINS

        # El crm editado se marca is_default=False
        assert policies["crm"]["mode"] == "MANUAL"
        assert policies["crm"]["is_default"] is False

        # banking_write sin fila → MANUAL default
        assert policies["banking_write"]["mode"] == "MANUAL"
        assert policies["banking_write"]["is_default"] is True

    async def test_policies_aisladas_entre_tenants(
        self, db, seed_tenant_and_user
    ):
        tenant, _user, _token = seed_tenant_and_user
        from uuid import uuid4
        other = uuid4()

        await set_policy(db, tenant_id=tenant.id, domain="crm", mode="MANUAL")
        await db.commit()

        # El tenant principal ve MANUAL, otro tenant ve AUTO (default)
        assert await check_autonomy(db, tenant_id=tenant.id, domain="crm") == "MANUAL"
        assert await check_autonomy(db, tenant_id=other, domain="crm") == "AUTO"


class TestKnownDomains:
    def test_dominios_minimos_presentes(self):
        for d in ("banking_read", "banking_write", "accounting", "billing", "crm", "hr", "marketing", "recruitment"):
            assert d in KNOWN_DOMAINS, f"Falta dominio crítico: {d}"

    def test_defaults_solo_para_dominios_conocidos(self):
        for d in DEFAULTS:
            assert d in KNOWN_DOMAINS, f"DEFAULT para dominio no listado: {d}"
