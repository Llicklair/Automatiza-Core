"""Tests de negocio del agente compliance.

Cubren la validación de entrada y, sobre todo, el safeguard CONT.0: cuando el
calendario fiscal AEAT no se puede cargar, la tool NUNCA debe inventar fechas;
debe degradar a un mensaje que remita a la sede de la AEAT.
"""
from unittest.mock import patch

import pytest

from app.agents.compliance.tools import check_fiscal_deadlines, check_quarter_preventive

VALID_TENANT = "00000000-0000-0000-0000-000000000001"


# ── check_quarter_preventive: validación sin BD ───────────────────────────────

@pytest.mark.asyncio
async def test_preventive_rejects_bad_tenant_uuid():
    out = await check_quarter_preventive.ainvoke(
        {"tenant_id": "no-uuid", "quarter": 1, "year": 2026}
    )
    assert out.startswith("FAIL")
    assert "UUID" in out


@pytest.mark.asyncio
async def test_preventive_rejects_invalid_quarter():
    out = await check_quarter_preventive.ainvoke(
        {"tenant_id": VALID_TENANT, "quarter": 5, "year": 2026}
    )
    assert out.startswith("FAIL")
    assert "trimestre inválido" in out


# ── check_fiscal_deadlines: safeguard CONT.0 contra fechas caducadas ──────────

@pytest.mark.asyncio
async def test_deadlines_stale_calendar_does_not_invent_dates():
    def _boom(days_ahead=90):
        raise RuntimeError("AEAT calendar unavailable")

    with patch("app.agents.compliance.tools.get_proximos_vencimientos", side_effect=_boom):
        out = await check_fiscal_deadlines.ainvoke({"days_ahead": 90})

    # No debe contener fechas inventadas; debe remitir a la sede AEAT.
    assert "sede.agenciatributaria.gob.es" in out
    assert "no se ha podido cargar" in out.lower()


@pytest.mark.asyncio
async def test_deadlines_empty_calendar_message():
    def _none(days_ahead=90):
        return []

    with patch("app.agents.compliance.tools.get_proximos_vencimientos", side_effect=_none):
        out = await check_fiscal_deadlines.ainvoke({"days_ahead": 45})

    assert "No hay vencimientos" in out
    assert "45" in out
