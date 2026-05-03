"""Tests de aislamiento Row-Level Security contra Postgres real.

Estos tests validan que las políticas creadas por la migración 0003_enable_rls
bloquean efectivamente acceso cross-tenant. Requieren un Postgres con la
migración aplicada y se saltan automáticamente si no hay conectividad.

Variables de entorno:
- TEST_DATABASE_URL: URL postgresql+asyncpg de la BD de tests
  (default: postgresql+asyncpg://pyme_user:pyme_pass@localhost:5433/pyme_db_test)
- Si no se puede conectar en 3 segundos, los tests se saltan.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.tenant_context import (
    set_current_tenant,
    system_context,
    tenant_context,
)
from app.db.rls import register_rls_listener

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://pyme_user:pyme_pass@localhost:5433/pyme_db_test",
)


async def _can_connect(url: str) -> bool:
    try:
        engine = create_async_engine(url, connect_args={"timeout": 3})
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


@pytest_asyncio.fixture(scope="module")
async def pg_engine():
    if not await _can_connect(TEST_DB_URL):
        pytest.skip(
            "Postgres de tests no disponible. "
            "Levanta el contenedor y aplica la migración 0003_enable_rls."
        )
    eng = create_async_engine(TEST_DB_URL, pool_pre_ping=True)
    register_rls_listener(eng.sync_engine)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(pg_engine):
    sm = async_sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as s:
        yield s


@pytest_asyncio.fixture(scope="module")
async def two_tenants(pg_engine):
    """Crea dos tenants y un Client de cada uno como dato de prueba.

    Limpia al final del módulo para no contaminar otras suites.
    """
    sm = async_sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    cid_a = uuid.uuid4()
    cid_b = uuid.uuid4()

    async with sm() as s, system_context():
        await s.execute(
            text(
                "INSERT INTO tenants (id, name, jurisdiction, plan, created_at) "
                "VALUES (:id, :name, 'ES', 'free', now())"
            ),
            [{"id": tid_a, "name": "rls-test-A"}, {"id": tid_b, "name": "rls-test-B"}],
        )
        await s.execute(
            text(
                "INSERT INTO clients (id, tenant_id, name, created_at) "
                "VALUES (:id, :tid, :name, now())"
            ),
            [
                {"id": cid_a, "tid": tid_a, "name": "client-A"},
                {"id": cid_b, "tid": tid_b, "name": "client-B"},
            ],
        )
        await s.commit()

    yield {"a": str(tid_a), "b": str(tid_b), "client_a": str(cid_a), "client_b": str(cid_b)}

    async with sm() as s, system_context():
        await s.execute(text("DELETE FROM clients WHERE tenant_id IN (:a, :b)"), {"a": tid_a, "b": tid_b})
        await s.execute(text("DELETE FROM tenants WHERE id IN (:a, :b)"), {"a": tid_a, "b": tid_b})
        await s.commit()


@pytest.mark.asyncio
async def test_query_without_context_returns_zero_rows(session, two_tenants):
    """Sin tenant en contexto, las policies NULLIF(...) devuelven NULL → falso → 0 filas."""
    set_current_tenant(None)
    result = await session.execute(text("SELECT COUNT(*) FROM clients"))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_query_with_tenant_a_sees_only_tenant_a(session, two_tenants):
    with tenant_context(two_tenants["a"]):
        result = await session.execute(text("SELECT id::text, tenant_id::text FROM clients"))
        rows = result.all()

    assert len(rows) == 1
    assert rows[0].id == two_tenants["client_a"]
    assert rows[0].tenant_id == two_tenants["a"]


@pytest.mark.asyncio
async def test_query_with_tenant_b_sees_only_tenant_b(session, two_tenants):
    with tenant_context(two_tenants["b"]):
        result = await session.execute(text("SELECT id::text FROM clients"))
        ids = {r.id for r in result.all()}

    assert ids == {two_tenants["client_b"]}


@pytest.mark.asyncio
async def test_insert_with_wrong_tenant_id_is_rejected(session, two_tenants):
    """Si el ContextVar dice tenant A pero el row trae tenant_id=B,
    la WITH CHECK clause de la policy debe rechazar el INSERT."""
    bogus_id = uuid.uuid4()
    with tenant_context(two_tenants["a"]):
        with pytest.raises(Exception) as exc_info:
            await session.execute(
                text(
                    "INSERT INTO clients (id, tenant_id, name, created_at) "
                    "VALUES (:id, :tid, 'attacker', now())"
                ),
                {"id": bogus_id, "tid": two_tenants["b"]},
            )
            await session.commit()
        # Postgres lanza "new row violates row-level security policy"
        assert "row-level security" in str(exc_info.value).lower() or "policy" in str(exc_info.value).lower()
        await session.rollback()


@pytest.mark.asyncio
async def test_system_context_sees_all_tenants(session, two_tenants):
    """system_context() debe ver datos de todos los tenants (mantenimiento)."""
    with system_context():
        result = await session.execute(
            text("SELECT id::text FROM clients WHERE id IN (:a, :b)"),
            {"a": uuid.UUID(two_tenants["client_a"]), "b": uuid.UUID(two_tenants["client_b"])},
        )
        ids = {r.id for r in result.all()}

    assert ids == {two_tenants["client_a"], two_tenants["client_b"]}
