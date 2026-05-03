"""
Sesión SQLAlchemy síncrona para uso en agentes LLM y scripts.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _get_sync_url() -> str:
    """Convierte la URL async de asyncpg a psycopg2 para uso síncrono."""
    url = settings.DATABASE_URL
    # postgresql+asyncpg://... → postgresql+psycopg2://...
    return url.replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")


_sync_engine = create_engine(
    _get_sync_url(),
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

# El motor síncrono lo usan agentes y scripts. Aplica el mismo listener RLS
# para mantener una sola política de aislamiento, independientemente del driver.
from app.db.rls import register_rls_listener  # noqa: E402

register_rls_listener(_sync_engine)

SessionLocal = sessionmaker(
    bind=_sync_engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)
