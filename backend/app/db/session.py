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

SessionLocal = sessionmaker(
    bind=_sync_engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)
