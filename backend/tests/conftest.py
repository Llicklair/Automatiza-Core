"""
Fixtures compartidas para todos los tests.
Usa una BD SQLite async en memoria para no depender de PostgreSQL.
"""
import os
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest_asyncio
from cryptography.fernet import Fernet

# ── Variables de entorno ANTES de cualquier import de la app ──────────────────
os.environ["SECRET_KEY"] = "test_secret_key_do_not_use_in_production_1234567890abcdef"
os.environ["TENANT_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["FRONTEND_URL"] = "http://localhost:3000"

# Evita que pytest cree 'pytest-of-<user>' en la raíz del repo: si TEMP/TMP no
# están en el entorno, tempfile.gettempdir() cae al cwd (la raíz) como último
# recurso. Forzamos un temp real solo cuando falta toda variable de entorno.
if not (os.environ.get("TMPDIR") or os.environ.get("TEMP") or os.environ.get("TMP")):
    import tempfile

    _tmp = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Temp")
    os.makedirs(_tmp, exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = _tmp
    tempfile.tempdir = _tmp

# ── Parchear el engine de base.py para que use SQLite ────────────────────────
# base.py se ejecuta al importarse y crea un engine con pool_size (incompatible con SQLite).
# Lo parcheamos ANTES de importar la app.

# ── Hacer que JSONB compile como JSON en SQLite ──────────────────────────────
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

if not hasattr(SQLiteTypeCompiler, '_original_visit_JSON'):
    SQLiteTypeCompiler._original_visit_JSON = getattr(SQLiteTypeCompiler, 'visit_JSON', None)

def _visit_JSONB(self, type_, **kw):
    return "JSON"

SQLiteTypeCompiler.visit_JSONB = _visit_JSONB

# ── Hacer que BigInteger compile como INTEGER en SQLite (para autoincrement) ──
from sqlalchemy import BigInteger, Integer
from sqlalchemy import event as sa_event

_bigint_patch_registered = False

_test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

_TestSessionLocal = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Parchear ANTES de importar app
import app.db.base as db_base_module

db_base_module.engine = _test_engine
db_base_module.AsyncSessionLocal = _TestSessionLocal

# Ahora sí importar la app
from app.core.security import create_access_token, get_password_hash
from app.db.base import Base, get_db
from app.main import app

# ── Parchear BigInteger → Integer para SQLite autoincrement ──────────────────
if not _bigint_patch_registered:
    @sa_event.listens_for(Base.metadata, "before_create")
    def _patch_bigint_for_sqlite(target, connection, **kw):
        if connection.dialect.name == "sqlite":
            for table in target.tables.values():
                for col in table.columns:
                    if isinstance(col.type, BigInteger) and col.primary_key:
                        col.type = Integer()
    _bigint_patch_registered = True


# ── Setup/teardown de BD por test ─────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Crea todas las tablas antes de cada test y las borra después."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = _override_get_db

# ── Desactivar rate limiting en tests ────────────────────────────────────────
from app.middleware.rate_limit import limiter

limiter.enabled = False


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with _TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator:
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seed_tenant_and_user(db: AsyncSession):
    """Crea un tenant y usuario de prueba, devuelve (tenant, user, token)."""
    from app.db.models.models import Tenant, User

    tenant = Tenant(
        id=uuid4(),
        name="Empresa Test S.L.",
        nif="B12345678",
        plan="starter",
    )
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="test@empresa.com",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Usuario Test",
        role="admin",
    )
    db.add(user)
    await db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(tenant.id),
        "role": "admin",
    })

    return tenant, user, token


@pytest_asyncio.fixture
async def auth_client(client, seed_tenant_and_user):
    """Cliente con token de autenticación ya configurado."""
    _, _, token = seed_tenant_and_user
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def seed_second_tenant_and_user(db: AsyncSession):
    """Crea un SEGUNDO tenant + user para validar aislamiento multi-tenant."""
    from app.db.models.models import Tenant, User

    tenant = Tenant(
        id=uuid4(),
        name="Empresa Otra S.L.",
        nif="B99999999",
        plan="starter",
    )
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="otro@empresa.com",
        hashed_password=get_password_hash("OtherPass123!"),
        full_name="Usuario Otro",
        role="admin",
    )
    db.add(user)
    await db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(tenant.id),
        "role": "admin",
    })
    return tenant, user, token


@pytest_asyncio.fixture
async def auth_client_b(seed_second_tenant_and_user):
    """Segundo cliente HTTP autenticado como un tenant distinto."""
    from httpx import ASGITransport, AsyncClient
    _, _, token = seed_second_tenant_and_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac
