from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


_engine_kwargs: dict = {
    "echo": settings.DEBUG,
}

# SQLite no soporta pool_size/max_overflow/pool_pre_ping
if "sqlite" not in settings.DATABASE_URL:
    _engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
        }
    )

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# SEC.RLS — registra el listener que aplica `SET LOCAL app.current_tenant` en
# CADA statement de CUALQUIER sesión (get_db, tool_session, workers, servicios),
# leyendo el ContextVar de tenant. Sin esto, solo get_db aplicaba el scoping.
from app.db.rls import install_rls_listener  # noqa: E402

install_rls_listener(engine)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
