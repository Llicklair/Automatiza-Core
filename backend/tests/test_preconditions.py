"""Tests para el kill-switch de precondiciones (CONT.KILL)."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.system.preconditions import (
    REQUIRED_TABLES,
    check_invoice_preconditions,
)


@pytest.mark.asyncio
class TestPreconditions:
    async def test_check_invoice_preconditions_ok(self, db):
        """En el setup de tests todas las tablas se crean — debe pasar."""
        result = await check_invoice_preconditions(db)
        assert result["ok"] is True
        assert result["missing"] == []
        assert all(result["details"][t] is True for t in REQUIRED_TABLES)

    async def test_endpoint_get_preconditions(self):
        """El endpoint público devuelve el estado."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/system/preconditions")
        assert resp.status_code == 200
        data = resp.json()
        assert "ok" in data
        assert "details" in data
        assert "missing" in data

    async def test_required_tables_son_las_3_esperadas(self):
        """La constante REQUIRED_TABLES debe cubrir FAC.NUM + FAC.HASH + SEC.APR."""
        assert set(REQUIRED_TABLES) == {
            "invoice_series",         # FAC.NUM
            "verifactu_chain",        # FAC.HASH
            "fiscal_approval_log",    # SEC.APR
        }
