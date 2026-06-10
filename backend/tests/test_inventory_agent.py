"""Tests del agente de stock: estructura del grafo, registro de tools y
validación de entrada de las tools de escritura (ramas previas a la BD)."""
from unittest.mock import AsyncMock, patch

import pytest


# ── Estructura del grafo ──────────────────────────────────────────────────────

def test_graph_compiles():
    from app.agents.inventory.agent import graph
    assert graph is not None


def test_graph_has_expected_nodes():
    from app.agents.inventory.agent import graph
    names = set(graph.nodes.keys())
    assert "inventory_agent" in names
    assert "tools" in names
    assert "finalize" in names


def test_core_tools_registered():
    from app.agents.inventory.agent import tools
    names = {t.name for t in tools}
    expected = {
        "get_stock_overview",
        "list_low_stock",
        "find_products",
        "get_product_stock",
        "batch_adjust_stock",
        "batch_update_products",
    }
    assert expected <= names, f"Faltan tools: {expected - names}"


def test_tools_have_descriptions():
    from app.agents.inventory.agent import tools
    for t in tools:
        assert t.description, f"Tool {t.name} sin descripción"


# ── Validación de entrada (no requiere BD) ────────────────────────────────────

VALID_TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_adjust_rejects_invalid_op():
    from app.agents.inventory.tools import batch_adjust_stock
    out = await batch_adjust_stock.ainvoke(
        {"tenant_id": VALID_TENANT, "items_json": "[]", "op": "multiplicar"}
    )
    assert "op inválido" in out


@pytest.mark.asyncio
async def test_adjust_rejects_bad_json():
    from app.agents.inventory.tools import batch_adjust_stock
    out = await batch_adjust_stock.ainvoke(
        {"tenant_id": VALID_TENANT, "items_json": "{no json", "op": "set"}
    )
    assert "items_json inválido" in out


@pytest.mark.asyncio
async def test_adjust_rejects_empty_list():
    from app.agents.inventory.tools import batch_adjust_stock
    out = await batch_adjust_stock.ainvoke(
        {"tenant_id": VALID_TENANT, "items_json": "[]", "op": "set"}
    )
    assert "vacía" in out


@pytest.mark.asyncio
async def test_update_rejects_bad_tenant():
    from app.agents.inventory.tools import batch_update_products
    out = await batch_update_products.ainvoke(
        {"tenant_id": "no-uuid", "items_json": "[]"}
    )
    assert "no es un identificador válido" in out


# ── Formateadores de previsualización (puros) ─────────────────────────────────

def test_format_adjust_preview_shows_confirm_hint():
    from app.agents.inventory.tools import _format_adjust_preview
    res = {
        "op": "set", "dry_run": True, "total": 1, "ok": 1, "skipped": 0, "applied": 0,
        "plan": [{"status": "ok", "name": "Café", "sku": "C1", "ref": "C1",
                  "before": 10, "after": 50, "delta": 40}],
    }
    out = _format_adjust_preview(res)
    assert "PREVISUALIZACIÓN" in out
    assert "confirm=true" in out
    assert "10 → 50" in out


# ── Gate de autonomía (tareas y automatizaciones) ─────────────────────────────

_FAKE_PREVIEW = {
    "op": "set", "dry_run": True, "total": 1, "ok": 1, "skipped": 0, "applied": 0,
    "plan": [{"status": "ok", "name": "Café", "sku": "C1", "ref": "C1",
              "before": 10, "after": 50, "delta": 40}],
}
_ITEMS = '[{"ref":"C1","quantity":50}]'


def _decision(mode: str) -> AsyncMock:
    """Mock de evaluate_autonomy que devuelve una AutonomyDecision real."""
    from uuid import UUID

    from app.services.autonomy_gate import AutonomyDecision

    return AsyncMock(return_value=AutonomyDecision(
        mode=mode, domain="inventory", tenant_id=UUID(VALID_TENANT),
        action_summary="test",
    ))


@pytest.mark.asyncio
async def test_confirm_mode_queues_approval_not_apply():
    """Política CONFIRM con contexto de task → encola aprobación, no aplica."""
    import app.agents.inventory.tools as t

    with patch.object(t.batch_service, "batch_adjust_stock", new=AsyncMock(return_value=_FAKE_PREVIEW)) as svc, \
         patch.object(t, "evaluate_autonomy", new=_decision("CONFIRM")), \
         patch.object(t, "create_action_approval", new=AsyncMock(return_value="appr-123")) as appr:
        out = await t.batch_adjust_stock.ainvoke(
            {"tenant_id": VALID_TENANT, "items_json": _ITEMS, "op": "set"}
        )

    assert "pendientes de aprobación" in out.lower() or "aprobación" in out.lower()
    appr.assert_awaited_once()
    # batch_service solo se llamó para la PREVISUALIZACIÓN (dry_run=True), no para aplicar.
    assert svc.await_count == 1


@pytest.mark.asyncio
async def test_manual_mode_only_suggests():
    """Política MANUAL → no ejecuta ni encola; solo sugiere."""
    import app.agents.inventory.tools as t

    with patch.object(t.batch_service, "batch_adjust_stock", new=AsyncMock(return_value=_FAKE_PREVIEW)) as svc, \
         patch.object(t, "evaluate_autonomy", new=_decision("MANUAL")), \
         patch.object(t, "create_action_approval", new=AsyncMock()) as appr:
        out = await t.batch_adjust_stock.ainvoke(
            {"tenant_id": VALID_TENANT, "items_json": _ITEMS, "op": "set"}
        )

    assert "MANUAL" in out
    appr.assert_not_awaited()
    assert svc.await_count == 1  # solo la previsualización


@pytest.mark.asyncio
async def test_auto_mode_applies_directly():
    """Política AUTO → aplica sin pedir confirmación (sirve a automatizaciones)."""
    import app.agents.inventory.tools as t

    applied = dict(_FAKE_PREVIEW)
    applied["dry_run"] = False
    applied["applied"] = 1

    async def _svc(db, tid, items, **kw):
        return applied if kw.get("dry_run") is False else _FAKE_PREVIEW

    with patch.object(t.batch_service, "batch_adjust_stock", new=AsyncMock(side_effect=_svc)), \
         patch.object(t, "evaluate_autonomy", new=_decision("AUTO")), \
         patch.object(t, "create_action_approval", new=AsyncMock()) as appr:
        out = await t.batch_adjust_stock.ainvoke(
            {"tenant_id": VALID_TENANT, "items_json": _ITEMS, "op": "set"}
        )

    assert "APLICADO" in out
    appr.assert_not_awaited()
