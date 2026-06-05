"""Tests para app.services.accounting.period_close — cierre/reapertura de
periodos contables y comprobación de bloqueo (cobertura QA)."""

from datetime import date, datetime
from uuid import uuid4

import pytest

from app.services.accounting.period_close import (
    PeriodClosedError,
    close_period,
    contains_date,
    is_date_locked,
    list_periods,
    reopen_period,
)


def test_period_closed_error_mensaje():
    err = PeriodClosedError("1T 2025", date(2025, 2, 1))
    assert "1T 2025" in str(err)
    assert "2025-02-01" in str(err)
    assert err.period_label == "1T 2025"


@pytest.mark.asyncio
class TestClosePeriod:
    async def test_kind_invalido(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        with pytest.raises(ValueError, match="kind"):
            await close_period(db, tenant.id, user.id, 2025, "semana", 1)

    async def test_month_index_fuera_rango(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        with pytest.raises(ValueError, match="entre 1 y 12"):
            await close_period(db, tenant.id, user.id, 2025, "month", 13)

    async def test_quarter_index_fuera_rango(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        with pytest.raises(ValueError, match="entre 1 y 4"):
            await close_period(db, tenant.id, user.id, 2025, "quarter", 5)

    async def test_year_index_debe_ser_cero(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        with pytest.raises(ValueError, match="0 para ejercicio"):
            await close_period(db, tenant.id, user.id, 2025, "year", 1)

    async def test_cierra_mes_nuevo(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        p = await close_period(db, tenant.id, user.id, 2025, "month", 3, notes="cierre")
        assert p.status == "closed"
        assert p.year == 2025
        assert p.period_index == 3

    async def test_cierre_idempotente(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        p1 = await close_period(db, tenant.id, user.id, 2025, "quarter", 1)
        p2 = await close_period(db, tenant.id, user.id, 2025, "quarter", 1)
        assert p1.id == p2.id  # mismo periodo, no duplica


@pytest.mark.asyncio
class TestReopenPeriod:
    async def test_requiere_motivo(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        p = await close_period(db, tenant.id, user.id, 2025, "month", 1)
        with pytest.raises(ValueError, match="motivo"):
            await reopen_period(db, tenant.id, user.id, p.id, "  ")

    async def test_periodo_no_existe(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        with pytest.raises(LookupError):
            await reopen_period(db, tenant.id, user.id, uuid4(), "motivo válido")

    async def test_reabre_ok(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        p = await close_period(db, tenant.id, user.id, 2025, "month", 1)
        reopened = await reopen_period(db, tenant.id, user.id, p.id, "error de imputación")
        assert reopened.status == "reopened"
        assert reopened.reopen_reason == "error de imputación"


@pytest.mark.asyncio
class TestLockAndList:
    async def test_is_date_locked_true(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        await close_period(db, tenant.id, user.id, 2025, "month", 3)
        locked, label = await is_date_locked(db, tenant.id, date(2025, 3, 15))
        assert locked is True
        assert label == "03/2025"

    async def test_is_date_locked_false_fuera_de_rango(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        await close_period(db, tenant.id, user.id, 2025, "month", 3)
        locked, label = await is_date_locked(db, tenant.id, datetime(2025, 5, 1))
        assert locked is False
        assert label is None

    async def test_list_periods_filtra_por_year(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        await close_period(db, tenant.id, user.id, 2024, "year", 0)
        await close_period(db, tenant.id, user.id, 2025, "quarter", 2)
        todos = await list_periods(db, tenant.id)
        assert len(todos) == 2
        solo_2025 = await list_periods(db, tenant.id, year=2025)
        assert len(solo_2025) == 1
        assert solo_2025[0].year == 2025


def _period(kind, year, idx):
    from app.db.models.accounting import AccountingPeriod

    return AccountingPeriod(tenant_id=uuid4(), year=year, kind=kind, period_index=idx, status="closed")


def test_contains_date_ramas():
    assert contains_date(_period("month", 2025, 2), date(2025, 2, 28)) is True
    assert contains_date(_period("month", 2025, 2), date(2025, 3, 1)) is False
    assert contains_date(_period("quarter", 2025, 1), date(2025, 3, 31)) is True
    assert contains_date(_period("quarter", 2025, 1), date(2025, 4, 1)) is False
    assert contains_date(_period("year", 2025, 0), date(2025, 12, 31)) is True
    assert contains_date(_period("desconocido", 2025, 0), date(2025, 1, 1)) is False
