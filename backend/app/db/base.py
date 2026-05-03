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

# Registra el listener RLS sobre el sync_engine subyacente: SQLAlchemy
# comparte los eventos entre el AsyncEngine y su sync_engine, y los hooks
# tipo before_cursor_execute solo se exponen a nivel sync.
from app.db.rls import register_rls_listener  # noqa: E402

register_rls_listener(engine.sync_engine)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


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
