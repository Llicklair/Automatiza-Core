"""Tests para metered billing (OPS.OVR + OPS.CRON)."""
from decimal import Decimal

import pytest
from app.services.billing.metering import (
    CRON_CAP_GESTORIA_MAX,
    CRON_CAP_GESTORIA_PER_COMPANY,
    CRON_CAP_PRO_FLAT,
    INTERACTION_HARD_CAP_EXTRA,
    INTERACTION_OVERAGE_PRICE_EUR,
    INTERACTION_SOFT_CAP_PRO,
    INTERACTION_WARNING_THRESHOLD,
    compute_cron_cap,
    record_cron_execution,
    record_interaction,
)


class TestComputeCronCap:
    def test_pro_es_200_flat(self):
        assert compute_cron_cap("pro") == 200
        assert compute_cron_cap("pro", active_companies=10) == 200  # ignora companies

    def test_gestoria_escala_por_empresas(self):
        assert compute_cron_cap("gestoria", active_companies=1) == 200
        assert compute_cron_cap("gestoria", active_companies=5) == 1000
        assert compute_cron_cap("gestoria", active_companies=10) == 2000

    def test_gestoria_topa_a_2000(self):
        # 50 empresas → 200 × 50 = 10000, pero el tope es 2000
        assert compute_cron_cap("gestoria", active_companies=50) == 2000

    def test_solo_no_tiene_cron(self):
        assert compute_cron_cap("solo") == 0

    def test_constantes_consensuadas(self):
        assert INTERACTION_SOFT_CAP_PRO == 500
        assert INTERACTION_WARNING_THRESHOLD == 450
        assert INTERACTION_HARD_CAP_EXTRA == 1000
        assert INTERACTION_OVERAGE_PRICE_EUR == Decimal("0.05")
        assert CRON_CAP_PRO_FLAT == 200
        assert CRON_CAP_GESTORIA_PER_COMPANY == 200
        assert CRON_CAP_GESTORIA_MAX == 2000


@pytest.mark.asyncio
class TestRecordInteraction:
    async def test_primera_interaccion_pro_count_1(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        status = await record_interaction(db, tenant_id=tenant.id, tier="pro")
        await db.commit()
        assert status.count == 1
        assert status.warning is False
        assert status.overage_active is False

    async def test_warning_a_partir_de_450(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        # Saltamos al estado 450 directamente para no hacer 450 inserciones
        from app.services.billing.metering import _current_period, _get_or_create_interaction_row

        year, month = _current_period()
        row = await _get_or_create_interaction_row(db, tenant.id, year, month)
        row.count = 449
        await db.flush()

        status = await record_interaction(db, tenant_id=tenant.id, tier="pro")
        await db.commit()
        assert status.count == 450
        assert status.warning is True
        assert status.overage_active is False

    async def test_overage_a_500(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        from app.services.billing.metering import _current_period, _get_or_create_interaction_row

        year, month = _current_period()
        row = await _get_or_create_interaction_row(db, tenant.id, year, month)
        row.count = 499
        await db.flush()

        status = await record_interaction(db, tenant_id=tenant.id, tier="pro")
        await db.commit()
        assert status.count == 500
        assert status.warning is False
        assert status.overage_active is True
        assert status.overage_count == 0
        assert status.pending_overage_charge_eur == 0.0

    async def test_cobro_overage_por_extra(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        from app.services.billing.metering import _current_period, _get_or_create_interaction_row

        year, month = _current_period()
        row = await _get_or_create_interaction_row(db, tenant.id, year, month)
        row.count = 510  # 10 extras
        row.overage_count = 10
        await db.flush()

        status = await record_interaction(db, tenant_id=tenant.id, tier="pro")
        await db.commit()
        # count=511, overage_count=11, cobro=11×0.05 = 0.55
        assert status.count == 511
        assert status.overage_count == 11
        assert status.pending_overage_charge_eur == pytest.approx(0.55)

    async def test_hard_cap_a_1000_extras(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        from app.services.billing.metering import _current_period, _get_or_create_interaction_row

        year, month = _current_period()
        row = await _get_or_create_interaction_row(db, tenant.id, year, month)
        row.count = 1500
        row.overage_count = 1000
        await db.flush()

        status = await record_interaction(db, tenant_id=tenant.id, tier="pro")
        await db.commit()
        assert status.hard_cap_reached is True

    async def test_gestoria_sin_cap(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        # Aún con count alto, gestoria no marca overage
        from app.services.billing.metering import _current_period, _get_or_create_interaction_row

        year, month = _current_period()
        row = await _get_or_create_interaction_row(db, tenant.id, year, month)
        row.count = 2000
        await db.flush()

        status = await record_interaction(db, tenant_id=tenant.id, tier="gestoria")
        await db.commit()
        assert status.warning is False
        assert status.overage_active is False
        assert status.soft_cap is None


@pytest.mark.asyncio
class TestRecordCronExecution:
    async def test_pro_incrementa_hasta_cap(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        from app.services.billing.metering import _current_period, _get_or_create_cron_row

        year, month = _current_period()
        row = await _get_or_create_cron_row(db, tenant.id, year, month)
        row.count = 199
        await db.flush()

        status = await record_cron_execution(db, tenant_id=tenant.id, tier="pro")
        await db.commit()
        assert status.count == 200
        assert status.cap == 200
        assert status.cap_reached is True

    async def test_pro_rechaza_si_ya_en_cap(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        from app.services.billing.metering import _current_period, _get_or_create_cron_row

        year, month = _current_period()
        row = await _get_or_create_cron_row(db, tenant.id, year, month)
        row.count = 200
        await db.flush()

        status = await record_cron_execution(db, tenant_id=tenant.id, tier="pro")
        await db.commit()
        # count no debe incrementar porque ya estaba en cap
        assert status.count == 200
        assert status.cap_reached is True

    async def test_gestoria_escala_con_empresas(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        status = await record_cron_execution(
            db, tenant_id=tenant.id, tier="gestoria", active_companies=5,
        )
        await db.commit()
        assert status.cap == 1000
        assert status.cap_reached is False
