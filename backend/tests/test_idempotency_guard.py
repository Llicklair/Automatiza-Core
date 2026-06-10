"""IdempotencyGuard persistente en DB — sobrevive 'reinicios' (memoria limpia)."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select

import app.services.idempotency as idem
from app.db.models import IdempotencyKey
from app.services.idempotency import IdempotencyGuard, purge_expired_keys

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _clean_memory():
    idem._store.clear()
    yield
    idem._store.clear()


def _patched(db):
    @asynccontextmanager
    async def ctx():
        yield db

    return patch("app.db.base.AsyncSessionLocal", side_effect=ctx)


async def test_mark_executed_persiste_y_sobrevive_reinicio(db):
    guard = IdempotencyGuard()
    with _patched(db):
        await guard.mark_executed("recurring_invoice", "t1:2026-06", {"n": 1})

        row = (
            await db.execute(select(IdempotencyKey).where(
                IdempotencyKey.key == "idempotency:recurring_invoice:t1:2026-06"
            ))
        ).scalar_one()
        exp = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
        assert exp > datetime.now(UTC)  # sqlite devuelve naive; Postgres, aware

        # Simular reinicio: memoria vacía → debe leer de DB
        idem._store.clear()
        assert await guard.already_executed("recurring_invoice", "t1:2026-06") is True

        info = await guard.get_execution_info("recurring_invoice", "t1:2026-06")
        assert info["result"] == {"n": 1}


async def test_release_borra_la_clave(db):
    guard = IdempotencyGuard()
    with _patched(db):
        await guard.mark_executed("op", "x")
        await guard.release("op", "x")
        idem._store.clear()
        assert await guard.already_executed("op", "x") is False


async def test_clave_expirada_no_cuenta(db):
    guard = IdempotencyGuard()
    with _patched(db):
        db.add(IdempotencyKey(
            key="idempotency:op:viejo",
            payload="{}",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            created_at=datetime.now(UTC) - timedelta(days=1),
        ))
        await db.commit()
        assert await guard.already_executed("op", "viejo") is False

        deleted = await purge_expired_keys()
        assert deleted >= 1


async def test_fallback_a_memoria_si_db_falla():
    guard = IdempotencyGuard()
    with patch("app.db.base.AsyncSessionLocal", side_effect=RuntimeError("db down")):
        await guard.mark_executed("op", "y")
        assert await guard.already_executed("op", "y") is True
        await guard.release("op", "y")
        assert await guard.already_executed("op", "y") is False
