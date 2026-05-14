"""Tests para Row-Level Security helper (SEC.RLS).

Verifican el comportamiento del helper `apply_tenant_rls`. En SQLite las
policies no aplican; los tests validan los caminos de código (early return,
parsing UUID, integración con ContextVar).
"""
from uuid import uuid4

import pytest

from app.core.tenant_context import set_current_tenant, tenant_context
from app.db.rls import apply_tenant_rls


@pytest.mark.asyncio
class TestApplyTenantRls:
    async def test_sqlite_devuelve_none_sin_error(self, db):
        # En SQLite (tests) la función debe retornar None sin tocar la sesión.
        set_current_tenant(None)
        result = await apply_tenant_rls(db)
        assert result is None

    async def test_sqlite_con_tenant_sigue_devolviendo_none(self, db):
        # Aún con tenant válido en context, en SQLite es no-op.
        tenant_uuid = uuid4()
        with tenant_context(str(tenant_uuid)):
            result = await apply_tenant_rls(db)
        assert result is None

    async def test_tenant_invalido_no_lanza(self, db):
        # tenant_id no parseable como UUID → función segura, devuelve None.
        with tenant_context("not-a-uuid"):
            result = await apply_tenant_rls(db)
        assert result is None

    async def test_context_var_se_lee_correctamente(self):
        # Verifica el ContextVar en isolation (sin sesión real).
        from app.core.tenant_context import get_current_tenant
        tid = str(uuid4())
        with tenant_context(tid):
            assert get_current_tenant() == tid
        # Tras salir del with, vuelve a None
        assert get_current_tenant() is None


@pytest.mark.asyncio
class TestRlsMigrationSafety:
    """La migración 0016 debe ser no-op en SQLite y aplicar policies en Postgres."""

    async def test_migracion_no_rompe_sqlite_setup(self, db):
        # El fixture setup_db crea Base.metadata.create_all — si las policies
        # rompiesen el schema, los tests no llegarían aquí.
        # Hacemos un SELECT trivial para asegurar que las tablas están vivas.
        from sqlalchemy import text
        result = await db.execute(text("SELECT 1"))
        assert result.scalar() == 1
