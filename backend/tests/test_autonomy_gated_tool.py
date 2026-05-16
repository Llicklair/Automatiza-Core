"""Tests del decorator `gated_tool` (AI.AGT wiring)."""
from unittest.mock import patch

import pytest
from app.services.autonomy import set_policy
from app.services.autonomy_gate import gated_tool


@pytest.mark.asyncio
class TestGatedTool:
    """Verifica las 3 ramas AUTO/CONFIRM/MANUAL via el decorator."""

    def _patched_session(self, db):
        """Sync context manager que patcha AsyncSessionLocal para reusar `db`.

        El decorator hace `async with AsyncSessionLocal() as db: ...`,
        así que sustituimos la factoría por una que devuelve un async
        context manager que yieldea nuestro fixture.
        """
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def ctx():
            yield db

        return patch("app.db.base.AsyncSessionLocal", side_effect=ctx)

    async def test_auto_ejecuta_la_tool_real(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        # Forzamos AUTO en banking_write (el default es MANUAL).
        await set_policy(db, tenant_id=tenant.id, domain="banking_write", mode="AUTO")
        await db.commit()

        called = {"count": 0}

        @gated_tool(domain="banking_write")
        async def fake_tool(tenant_id: str, x: int = 1):
            called["count"] += 1
            return f"executed:{x}"

        with self._patched_session(db):
            result = await fake_tool(tenant_id=str(tenant.id), x=42)

        assert result == "executed:42"
        assert called["count"] == 1

    async def test_confirm_devuelve_pendiente_y_no_ejecuta(
        self, db, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user
        await set_policy(db, tenant_id=tenant.id, domain="banking_write", mode="CONFIRM")
        await db.commit()

        called = {"count": 0}

        @gated_tool(
            domain="banking_write",
            summary_fn=lambda kw: f"transferir {kw['amount']}€",
        )
        async def fake_transfer(tenant_id: str, amount: float):
            called["count"] += 1
            return "real-transfer-done"

        with self._patched_session(db):
            result = await fake_transfer(tenant_id=str(tenant.id), amount=100.0)

        assert called["count"] == 0
        assert "pendiente" in result.lower()
        assert "transferir 100" in result

    async def test_manual_devuelve_sugerencia(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        # banking_write default MANUAL, no es necesario set explícito.
        called = {"count": 0}

        @gated_tool(domain="banking_write")
        async def fake_tool(tenant_id: str):
            called["count"] += 1
            return "x"

        with self._patched_session(db):
            result = await fake_tool(tenant_id=str(tenant.id))

        assert called["count"] == 0
        assert "MANUAL" in result

    async def test_sin_tenant_id_ejecuta_sin_gate(self, db, seed_tenant_and_user):
        """Si la tool no recibe tenant_id, no se puede gatear — ejecuta."""
        called = {"count": 0}

        @gated_tool(domain="banking_write")
        async def fake_tool():
            called["count"] += 1
            return "ok"

        with self._patched_session(db):
            result = await fake_tool()

        assert called["count"] == 1
        assert result == "ok"

    async def test_tenant_id_no_uuid_ejecuta_sin_gate(
        self, db, seed_tenant_and_user
    ):
        """Si el tenant_id no es UUID válido, no se puede gatear — ejecuta."""
        called = {"count": 0}

        @gated_tool(domain="banking_write")
        async def fake_tool(tenant_id: str):
            called["count"] += 1
            return "ok"

        with self._patched_session(db):
            result = await fake_tool(tenant_id="not-a-uuid")

        assert called["count"] == 1

    async def test_summary_default_menciona_tool_y_dominio(
        self, db, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user

        @gated_tool(domain="banking_write")  # default MANUAL
        async def my_specific_tool(tenant_id: str):
            return "x"

        with self._patched_session(db):
            result = await my_specific_tool(tenant_id=str(tenant.id))

        assert "my_specific_tool" in result
        assert "banking_write" in result

    async def test_dominio_crm_default_auto_ejecuta(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        called = {"count": 0}

        @gated_tool(domain="crm")  # default AUTO
        async def fake_tool(tenant_id: str):
            called["count"] += 1
            return "crm-result"

        with self._patched_session(db):
            result = await fake_tool(tenant_id=str(tenant.id))

        assert called["count"] == 1
        assert result == "crm-result"
