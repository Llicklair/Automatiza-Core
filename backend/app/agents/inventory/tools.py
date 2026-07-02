"""Inventory (stock) agent — tools de consulta y de modificación por lotes.

Las tools de escritura siguen el patrón PREVISUALIZAR→CONFIRMAR: con confirm=False
devuelven un resumen de los cambios sin tocar la BD; con confirm=True los aplican.
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import or_, select

from app.agents.agent_tools.reports import create_pdf_report, create_pdf_text_report
from app.agents.shared.db import tool_session
from app.db.models.inventory import Product
from app.services.autonomy_gate import evaluate_autonomy
from app.services.inventory import analytics, batch_service, reorder_service
from app.services.workflow.approval_actions import create_action_approval

logger = logging.getLogger(__name__)

# Dominio de autonomía para las escrituras de stock (ver services/autonomy.py).
_INVENTORY_DOMAIN = "inventory"


def _parse_uuid(value: str, label: str = "tenant_id") -> UUID:
    try:
        return UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"{label} '{value}' no es un identificador válido.") from exc


def _parse_items(items_json: str) -> list[dict]:
    data = json.loads(items_json) if isinstance(items_json, str) else items_json
    if not isinstance(data, list):
        raise ValueError("items_json debe ser una lista JSON.")
    return data


# ── Consultas ─────────────────────────────────────────────────────────────────


@tool
async def get_stock_overview(tenant_id: str) -> str:
    """Resumen del inventario: valoración (coste, PVP, margen), nº de productos con
    stock, recuento de stock muerto y productos más movidos."""
    try:
        tid = _parse_uuid(tenant_id)
    except ValueError as e:
        return f"Error: {e}"
    try:
        async with tool_session(tid) as db:
            ov = await analytics.inventory_overview(db, tid)
    except Exception as e:
        logger.warning("get_stock_overview falló: %s", e)
        return f"Error al obtener el resumen de inventario: {e}"

    v = ov["valuation"]
    lines = [
        "Resumen de inventario:",
        f"- Productos activos con stock: {v['product_count']} ({v['units']} unidades)",
        f"- Valoración a coste: {v['value_cost']:.2f}€",
        f"- Valoración a PVP: {v['value_retail']:.2f}€ (margen potencial {v['potential_margin']:.2f}€)",
        f"- Stock muerto (>{ov['dead_days']}d sin movimiento): {ov['dead_count']} productos, {ov['dead_value_cost']:.2f}€ a coste",
    ]
    if ov["top_movers"]:
        lines.append(
            "- Más movidos: " + ", ".join(f"{m.get('name', '?')} ({m.get('units', 0)})" for m in ov["top_movers"][:5])
        )
    return "\n".join(lines)


@tool
async def list_low_stock(tenant_id: str) -> str:
    """Lista los productos en o por debajo de su punto de pedido (stock mínimo),
    con la cantidad de reposición sugerida y el proveedor."""
    try:
        tid = _parse_uuid(tenant_id)
    except ValueError as e:
        return f"Error: {e}"
    try:
        async with tool_session(tid) as db:
            rows = await reorder_service.suggest_reorders(db, tid)
    except Exception as e:
        logger.warning("list_low_stock falló: %s", e)
        return f"Error al consultar stock bajo: {e}"

    if not rows:
        return "No hay productos por debajo de su punto de pedido."
    lines = [f"Productos bajo mínimo ({len(rows)}):"]
    for r in rows:
        prov = f" | Proveedor: {r['supplier_name']}" if r.get("supplier_name") else ""
        lines.append(
            f"- {r['name']} ({r.get('sku') or 's/SKU'}): {r['current_stock']} uds "
            f"(mín {r['reorder_point']}, pedir ~{r['suggested_qty']}){prov}"
        )
    return "\n".join(lines)


@tool
async def find_products(tenant_id: str, query: str = "", category: str = "") -> str:
    """Busca productos por nombre, SKU o código de barras (query) y/o categoría.
    Devuelve hasta 30 con su stock actual y precio."""
    try:
        tid = _parse_uuid(tenant_id)
    except ValueError as e:
        return f"Error: {e}"
    try:
        async with tool_session(tid) as db:
            stmt = select(Product).where(Product.tenant_id == tid)
            if query:
                like = f"%{query}%"
                stmt = stmt.where(or_(Product.name.ilike(like), Product.sku.ilike(like), Product.barcode.ilike(like)))
            if category:
                stmt = stmt.where(Product.category.ilike(f"%{category}%"))
            stmt = stmt.order_by(Product.name.asc()).limit(30)
            res = await db.execute(stmt)
            products = res.scalars().all()
    except Exception as e:
        logger.warning("find_products falló: %s", e)
        return f"Error al buscar productos: {e}"

    if not products:
        return "No se encontraron productos con esos criterios."
    lines = [f"Productos ({len(products)}):"]
    for p in products:
        estado = "" if p.is_active else " [INACTIVO]"
        lines.append(
            f"- {p.name} | SKU: {p.sku or '—'} | Stock: {int(p.stock_quantity or 0)} "
            f"| PVP: {float(p.price or 0):.2f}€ | Cat: {p.category or '—'}{estado}"
        )
    return "\n".join(lines)


@tool
async def get_product_stock(tenant_id: str, ref: str) -> str:
    """Detalle de stock de un producto concreto (por SKU, código de barras, nombre o ID)."""
    try:
        tid = _parse_uuid(tenant_id)
    except ValueError as e:
        return f"Error: {e}"
    try:
        async with tool_session(tid) as db:
            product, how = await batch_service.resolve_product(db, tid, ref)
            if product is None:
                return f"No se pudo identificar el producto '{ref}': {how}."
            return (
                f"{product.name} (SKU: {product.sku or '—'}, ID: {product.id})\n"
                f"- Stock actual: {int(product.stock_quantity or 0)} {product.unit or 'ud'}\n"
                f"- Stock mínimo: {int(product.stock_min_alert or 0)}\n"
                f"- Precio: {float(product.price or 0):.2f}€ | Coste: "
                f"{float(product.cost_price) if product.cost_price is not None else 0:.2f}€ | IVA: {float(product.tax_percentage or 0):.0f}%\n"
                f"- Categoría: {product.category or '—'} | Ubicación: {product.location or '—'}\n"
                f"- Activo: {'sí' if product.is_active else 'no'}"
            )
    except Exception as e:
        logger.warning("get_product_stock falló: %s", e)
        return f"Error al consultar el producto: {e}"


# ── Helpers de formato de previsualización ────────────────────────────────────


def _format_adjust_preview(res: dict) -> str:
    verb = {"set": "Recuento (fijar)", "add": "Entrada", "remove": "Salida"}[res["op"]]
    head = "PREVISUALIZACIÓN" if res["dry_run"] else "APLICADO"
    lines = [f"{head} — {verb} de stock | {res['ok']} OK, {res['skipped']} omitidos de {res['total']}:"]
    for r in res["plan"]:
        if r["status"] == "ok":
            lines.append(
                f"  • {r['name']} ({r.get('sku') or r['ref']}): {r['before']} → {r['after']} ({r['delta']:+d})"
            )
        else:
            lines.append(f"  ⚠️ {r['ref']}: {r.get('warning', r['status'])}")
    if res["dry_run"] and res["ok"] > 0:
        lines.append("\nPara aplicar estos cambios, vuelve a llamar con confirm=true.")
    elif not res["dry_run"]:
        lines.append(f"\n{res['applied']} movimientos de stock registrados.")
    return "\n".join(lines)


def _format_update_preview(res: dict) -> str:
    head = "PREVISUALIZACIÓN" if res["dry_run"] else "APLICADO"
    lines = [f"{head} — Actualización de catálogo | {res['ok']} OK, {res['skipped']} omitidos de {res['total']}:"]
    for r in res["plan"]:
        if r["status"] == "ok":
            chg = ", ".join(f"{f}: {c['before']}→{c['after']}" for f, c in r["changes"].items())
            lines.append(f"  • {r['name']} ({r.get('sku') or r['ref']}): {chg}")
        else:
            lines.append(f"  ⚠️ {r['ref']}: {r.get('warning', r['status'])}")
    if res["dry_run"] and res["ok"] > 0:
        lines.append("\nPara aplicar estos cambios, vuelve a llamar con confirm=true.")
    elif not res["dry_run"]:
        lines.append(f"\n{res['applied']} productos actualizados.")
    return "\n".join(lines)


# ── Gate de autonomía (tareas y automatizaciones) ─────────────────────────────


async def _gated_batch(tenant_uuid, *, kind, params, summary, confirm, apply_fn):
    """Aplica una escritura de stock respetando la política de autonomía.

    - AUTO    → ejecuta directamente (sin confirmación; sirve a automatizaciones).
    - CONFIRM → encola una PendingApproval (bandeja de aprobaciones). Funciona
                igual en tarea interactiva que en automatización: la acción se
                aprueba luego y se ejecuta vía el executor registrado.
                Si no hay contexto de task (uso suelto), cae a confirm=true.
    - MANUAL  → solo sugiere, no ejecuta.

    `apply_fn(db)` ejecuta la escritura real (dry_run=False) y devuelve el dict
    de resultado; el caller lo formatea.
    """
    async with tool_session(tenant_uuid) as db:
        decision = await evaluate_autonomy(
            db,
            tenant_id=tenant_uuid,
            domain=_INVENTORY_DOMAIN,
            action_summary=summary[:480],
            action_payload=params,
        )

    if decision.manual_only:
        return (
            "⚠ Política de inventario en MANUAL: no aplico cambios automáticamente. "
            "Revisa la previsualización y aplícalos desde la UI.\n\n" + summary
        )

    if decision.needs_approval:
        # create_action_approval (y no decision.persist_pending_approval) porque
        # descubre el task-context activo y es idempotente por task/execution.
        approval_id = await create_action_approval(
            tenant_id=str(tenant_uuid), kind=kind, params=params, summary=summary[:480]
        )
        if approval_id:
            return (
                "⏸ Cambios pendientes de aprobación (inventario = CONFIRM). "
                "Los he enviado a la bandeja de aprobaciones; se aplicarán al aprobarlos.\n\n" + summary
            )
        # Sin contexto de task (uso interactivo suelto): confirmación clásica.
        if not confirm:
            return summary + "\n\nPara aplicar estos cambios, repite la operación con confirm=true."

    # AUTO, o CONFIRM aprobado de forma interactiva.
    async with tool_session(tenant_uuid) as db:
        res = await apply_fn(db)
    return res


# ── Modificación por lotes (preview + confirm) ────────────────────────────────


@tool
async def batch_adjust_stock(
    tenant_id: str,
    items_json: str,
    op: str = "set",
    reason: str = "",
    confirm: bool = False,
) -> str:
    """Ajusta el stock de varios productos a la vez. PREVISUALIZA con confirm=false
    y APLICA con confirm=true.

    Args:
        tenant_id: UUID del tenant.
        items_json: JSON array, ej. '[{"ref":"SKU-001","quantity":50}]'. `ref` puede
            ser SKU, código de barras, nombre o ID.
        op: 'set' (recuento: fija la cantidad), 'add' (entrada: suma),
            'remove' (salida/merma: resta).
        reason: motivo del ajuste (queda en el histórico de movimientos).
        confirm: False = previsualizar sin tocar la BD; True = aplicar.
    """
    try:
        tid = _parse_uuid(tenant_id)
    except ValueError as e:
        return f"Error: {e}"
    if op not in ("set", "add", "remove"):
        return "Error: op inválido. Usa 'set', 'add' o 'remove'."
    try:
        items = _parse_items(items_json)
    except (json.JSONDecodeError, ValueError) as e:
        return f"Error: items_json inválido ({e})."
    if not items:
        return "Error: la lista de productos está vacía."

    try:
        # Previsualización (no toca la BD) para el resumen de la aprobación.
        async with tool_session(tid) as db:
            preview = await batch_service.batch_adjust_stock(db, tid, items, op=op, reason=reason, dry_run=True)
        summary = _format_adjust_preview(preview)

        async def _apply(db):
            res = await batch_service.batch_adjust_stock(db, tid, items, op=op, reason=reason, dry_run=False)
            return _format_adjust_preview(res)

        return await _gated_batch(
            tid,
            kind="inventory_batch_adjust",
            params={"op": op, "items": items, "reason": reason},
            summary=summary,
            confirm=confirm,
            apply_fn=_apply,
        )
    except Exception as e:
        logger.warning("batch_adjust_stock falló: %s", e)
        return f"Error al ajustar el stock: {e}"


@tool
async def batch_update_products(
    tenant_id: str,
    items_json: str,
    confirm: bool = False,
) -> str:
    """Actualiza campos de catálogo de varios productos a la vez (precio, coste,
    % IVA, stock mínimo, categoría, ubicación, activo/inactivo).
    PREVISUALIZA con confirm=false y APLICA con confirm=true.

    Args:
        tenant_id: UUID del tenant.
        items_json: JSON array, ej.
            '[{"ref":"SKU-001","fields":{"price":19.99,"category":"Bebidas"}}]'.
            Campos válidos: price, cost_price, tax_percentage, stock_min_alert,
            category, location, is_active.
        confirm: False = previsualizar sin tocar la BD; True = aplicar.
    """
    try:
        tid = _parse_uuid(tenant_id)
    except ValueError as e:
        return f"Error: {e}"
    try:
        items = _parse_items(items_json)
    except (json.JSONDecodeError, ValueError) as e:
        return f"Error: items_json inválido ({e})."
    if not items:
        return "Error: la lista de productos está vacía."

    try:
        async with tool_session(tid) as db:
            preview = await batch_service.batch_update_fields(db, tid, items, dry_run=True)
        summary = _format_update_preview(preview)

        async def _apply(db):
            res = await batch_service.batch_update_fields(db, tid, items, dry_run=False)
            return _format_update_preview(res)

        return await _gated_batch(
            tid,
            kind="inventory_batch_update",
            params={"items": items},
            summary=summary,
            confirm=confirm,
            apply_fn=_apply,
        )
    except Exception as e:
        logger.warning("batch_update_products falló: %s", e)
        return f"Error al actualizar productos: {e}"


tools = [
    get_stock_overview,
    list_low_stock,
    find_products,
    get_product_stock,
    batch_adjust_stock,
    batch_update_products,
    create_pdf_report,
    create_pdf_text_report,
]


# Defensa multi-tenant: forzar tenant_id del ContextVar, no del LLM.
from app.agents.tenant_context import isolated as _isolated

tools = _isolated(tools)
