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


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            # SEC.RLS — aplicar `SET LOCAL app.current_tenant` si hay tenant
            # en el ContextVar (lo setea TenantContextMiddleware tras decodificar
            # el JWT). En SQLite (tests) la función no hace nada.
            from app.db.rls import apply_tenant_rls
            await apply_tenant_rls(session)

            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
