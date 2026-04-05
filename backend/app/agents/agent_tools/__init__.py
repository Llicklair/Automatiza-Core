# agent_tools package
from contextlib import contextmanager

from app.db.session import SessionLocal


@contextmanager
def get_sync_db():
    """Context manager for synchronous DB sessions in agent tools."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
