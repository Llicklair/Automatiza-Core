"""Tests del agente de stock: estructura del grafo, registro de tools y
validación de entrada de las tools de escritura (ramas previas a la BD)."""
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
