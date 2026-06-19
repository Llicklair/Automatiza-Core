"""SEC.RLS Fase C — verificación end-to-end de la RLS fail-closed contra Postgres.

El resto de la suite corre sobre SQLite en memoria, donde el listener de
`app.db.rls` es un no-op deliberado (la RLS es Postgres-only). Por eso esos tests
prueban el scoping a nivel de aplicación, pero NO la policy fail-closed real.

Estos tests levantan una BD Postgres **desechable** y ejercitan la cadena
completa, exactamente como en producción::

    set_current_tenant() / rls_bypass()        (ContextVar, app.core.tenant_context)
        → listener before_cursor_execute       (SET LOCAL app.current_tenant / app.rls_bypass)
            → policy ensure_rls_policies()      (USING / WITH CHECK fail-closed)

Conectan como el rol de aplicación `pyme_app` (NOSUPERUSER NOBYPASSRLS), igual
que el runtime: un superusuario ignoraría toda la RLS y el test no probaría nada.

Se **saltan automáticamente** si no hay un Postgres admin alcanzable (p. ej. CI
sin Postgres). Todo es configurable por entorno::

    RLS_TEST_PG_HOST (localhost)   RLS_TEST_PG_PORT (5433)
    RLS_TEST_ADMIN_USER (pyme_user)  RLS_TEST_ADMIN_PASSWORD (pyme_pass)
    RLS_TEST_APP_USER (pyme_app)     RLS_TEST_APP_PASSWORD (pyme_pass)
    RLS_TEST_DB (pyme_rls_phase_c_test)
"""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest

asyncpg = pytest.importorskip("asyncpg")

import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import DBAPIError  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.tenant_context import rls_bypass, set_current_tenant  # noqa: E402
from app.db.rls import install_rls_listener  # noqa: E402
from app.db.security_bootstrap import ensure_app_role, ensure_rls_policies  # noqa: E402

PG_HOST = os.getenv("RLS_TEST_PG_HOST", "localhost")
PG_PORT = int(os.getenv("RLS_TEST_PG_PORT", "5433"))
ADMIN_USER = os.getenv("RLS_TEST_ADMIN_USER", "pyme_user")
ADMIN_PASS = os.getenv("RLS_TEST_ADMIN_PASSWORD", "pyme_pass")
APP_USER = os.getenv("RLS_TEST_APP_USER", "pyme_app")
APP_PASS = os.getenv("RLS_TEST_APP_PASSWORD", "pyme_pass")
TEST_DB = os.getenv("RLS_TEST_DB", "pyme_rls_phase_c_test")

ADMIN_DSN = f"postgresql+asyncpg://{ADMIN_USER}:{ADMIN_PASS}@{PG_HOST}:{PG_PORT}/{TEST_DB}"
APP_DSN = f"postgresql+asyncpg://{APP_USER}:{APP_PASS}@{PG_HOST}:{PG_PORT}/{TEST_DB}"

# Dos tenants sembrados como admin (que bypassa RLS): A tiene 2 filas, B tiene 1.
TENANT_A = uuid4()
TENANT_B = uuid4()
SEED = [
    {"t": str(TENANT_A), "l": "A-1"},
    {"t": str(TENANT_A), "l": "A-2"},
    {"t": str(TENANT_B), "l": "B-1"},
]


# ── Setup/teardown de la BD desechable (síncrono → loop propio vía asyncio.run) ──
# Se hace en un fixture SÍNCRONO a propósito: corre fuera del event loop que
# pytest-asyncio crea para cada test, evitando conflictos de scope de loop.


async def _admin_connect(database: str):
    return await asyncio.wait_for(
        asyncpg.connect(
            host=PG_HOST, port=PG_PORT, user=ADMIN_USER,
            password=ADMIN_PASS, database=database,
        ),
        timeout=5,
    )


def _setup_schema(sync_conn) -> None:
    """Crea la tabla sonda y aplica los objetos de seguridad REALES del proyecto."""
    sync_conn.execute(
        text(
            "CREATE TABLE rls_probe ("
            "  id serial PRIMARY KEY,"
            "  tenant_id uuid NOT NULL,"
            "  label text NOT NULL"
            ")"
        )
    )
    ensure_app_role(sync_conn)       # rol pyme_app + grants (fuente de verdad real)
    ensure_rls_policies(sync_conn)   # ENABLE + FORCE RLS + policy fail-closed real


async def _provision() -> None:
    # 1) BD limpia.
    conn = await _admin_connect("postgres")
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        await conn.close()
    # 2) Esquema + seguridad + semilla (como admin → bypassa RLS al sembrar).
    engine = create_async_engine(ADMIN_DSN)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(_setup_schema)
            await conn.execute(
                text("INSERT INTO rls_probe (tenant_id, label) VALUES (CAST(:t AS uuid), :l)"),
                SEED,
            )
    finally:
        await engine.dispose()


async def _teardown() -> None:
    conn = await _admin_connect("postgres")
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
    finally:
        await conn.close()


@pytest.fixture(scope="module")
def pg_rls_db():
    # Skip si no hay Postgres admin alcanzable (CI sin PG, etc.).
    async def _probe():
        c = await _admin_connect("postgres")
        await c.close()

    try:
        asyncio.run(_probe())
    except Exception as exc:  # noqa: BLE001 — cualquier fallo de conexión → skip
        pytest.skip(f"Postgres admin no alcanzable en {PG_HOST}:{PG_PORT} ({exc})")

    asyncio.run(_provision())
    try:
        yield
    finally:
        try:
            asyncio.run(_teardown())
        except Exception:  # noqa: BLE001 — limpieza best-effort
            pass


@pytest_asyncio.fixture
async def app_engine(pg_rls_db):
    """Engine conectado como `pyme_app` (NOBYPASSRLS) con el listener RLS real."""
    engine = create_async_engine(APP_DSN)
    install_rls_listener(engine)
    set_current_tenant(None)
    try:
        yield engine
    finally:
        set_current_tenant(None)
        await engine.dispose()


async def _count(engine) -> int:
    async with engine.connect() as conn:
        return (await conn.execute(text("SELECT count(*) FROM rls_probe"))).scalar()


def _pg_sqlstate(exc) -> str | None:
    """Devuelve el SQLSTATE de Postgres recorriendo la cadena de excepciones.

    SQLAlchemy envuelve el error de asyncpg en su propio wrapper de dialecto, así
    que el código no está en el objeto de más arriba. Buscar el SQLSTATE (en vez
    del texto del mensaje) hace el assert independiente del idioma de Postgres.
    """
    seen: set[int] = set()
    stack = [exc]
    while stack:
        cur = stack.pop()
        if cur is None or id(cur) in seen:
            continue
        seen.add(id(cur))
        code = getattr(cur, "sqlstate", None) or getattr(cur, "pgcode", None)
        if code:
            return code
        stack += [getattr(cur, "orig", None), cur.__cause__, cur.__context__]
    return None


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_tenant_scoped_select_solo_ve_su_tenant(app_engine):
    """Con tenant fijado, la SELECT solo devuelve filas de ESE tenant."""
    set_current_tenant(str(TENANT_A))
    async with app_engine.connect() as conn:
        labels = (
            await conn.execute(text("SELECT label FROM rls_probe ORDER BY label"))
        ).scalars().all()
    assert labels == ["A-1", "A-2"]  # NO ve "B-1"


async def test_sin_tenant_es_fail_closed(app_engine):
    """Sin tenant y sin bypass: CERO filas (fail-closed, no fail-open)."""
    set_current_tenant(None)
    assert await _count(app_engine) == 0


async def test_rls_bypass_ve_todos_los_tenants(app_engine):
    """rls_bypass() activa app.rls_bypass='on' → la policy deja pasar todo."""
    set_current_tenant(None)
    with rls_bypass():
        total = await _count(app_engine)
    assert total == len(SEED)  # ve filas de A y de B
    # Y al salir del context manager, vuelve a fail-closed.
    assert await _count(app_engine) == 0


async def test_with_check_permite_insert_del_propio_tenant(app_engine):
    """Control positivo: insertar en el propio tenant SÍ pasa el WITH CHECK."""
    set_current_tenant(str(TENANT_A))
    async with app_engine.connect() as conn:
        trans = await conn.begin()
        await conn.execute(
            text("INSERT INTO rls_probe (tenant_id, label) VALUES (CAST(:t AS uuid), :l)"),
            {"t": str(TENANT_A), "l": "A-nuevo"},
        )
        await trans.rollback()  # no contaminamos la semilla compartida


async def test_with_check_bloquea_insert_cross_tenant(app_engine):
    """Insertar una fila de OTRO tenant viola el WITH CHECK → error."""
    set_current_tenant(str(TENANT_A))
    with pytest.raises(DBAPIError) as exc_info:
        async with app_engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO rls_probe (tenant_id, label) VALUES (CAST(:t AS uuid), :l)"),
                {"t": str(TENANT_B), "l": "intruso"},
            )
    # Comprobamos el SQLSTATE, no el texto (Postgres localiza el mensaje).
    # 42501 = insufficient_privilege, el código de una violación de la clausula
    # WITH CHECK de RLS. El control positivo anterior ya demuestra que pyme_app
    # SÍ tiene grant de INSERT, así que este 42501 solo puede ser la RLS.
    assert _pg_sqlstate(exc_info.value) == "42501"


async def test_using_oculta_filas_de_otro_tenant_en_update(app_engine):
    """La clausula USING también filtra escrituras: un UPDATE sobre filas de otro
    tenant no las ve → 0 filas afectadas (sin error, simplemente invisibles)."""
    set_current_tenant(str(TENANT_A))
    async with app_engine.connect() as conn:
        trans = await conn.begin()
        result = await conn.execute(
            text("UPDATE rls_probe SET label = 'hijacked' WHERE tenant_id = CAST(:t AS uuid)"),
            {"t": str(TENANT_B)},
        )
        await trans.rollback()
    assert result.rowcount == 0
