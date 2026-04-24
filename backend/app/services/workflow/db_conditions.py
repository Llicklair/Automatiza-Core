"""
Pre-fetch de condiciones basadas en BD para workflows.

Recorre el arbol de condiciones, identifica hojas con "provider",
ejecuta los queries y enriquece el contexto antes de la evaluacion.
El evaluador sincrono (conditions.py) nunca cambia.

Uso:
    from app.services.workflow.db_conditions import resolve_db_conditions
    ctx = await resolve_db_conditions(condition_tree, tenant_id, db, temporal_ctx)
    if not evaluate_conditions(condition_tree, ctx):
        ...
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.workflow.db_query_providers import QUERY_PROVIDERS

logger = logging.getLogger(__name__)


def _collect_provider_leaves(condition: dict | None) -> list[dict]:
    """Recorre el arbol de condiciones y retorna todas las hojas con 'provider'."""
    if not condition:
        return []

    operator = condition.get("operator", "").upper()

    if operator == "AND" or operator == "OR":
        leaves: list[dict] = []
        for child in condition.get("conditions", []):
            leaves.extend(_collect_provider_leaves(child))
        return leaves

    if operator == "NOT":
        return _collect_provider_leaves(condition.get("condition"))

    if "provider" in condition:
        return [condition]

    return []


async def resolve_db_conditions(
    condition: dict | None,
    tenant_id: UUID,
    db: AsyncSession,
    context: dict,
) -> dict:
    """
    Resuelve hojas provider consultando la BD e inyecta resultados en el contexto.

    Cada hoja {"provider": "billing.pending_invoice_count", "params": {...}, "op": "gt", "value": 10}
    se transforma: se le agrega "field": "db.billing.pending_invoice_count"
    y context["db"]["billing"]["pending_invoice_count"] = <resultado>.

    Retorna el contexto enriquecido. Si no hay hojas provider, retorna el contexto sin cambios.
    """
    leaves = _collect_provider_leaves(condition)
    if not leaves:
        return context

    db_ctx: dict = {}

    for leaf in leaves:
        provider_key = leaf["provider"]
        params = leaf.get("params", {})

        fn = QUERY_PROVIDERS.get(provider_key)
        if fn is None:
            logger.warning("[DB_CONDITIONS] Provider desconocido: %s", provider_key)
            leaf["field"] = f"db.{provider_key}"
            continue

        try:
            value = await fn(tenant_id, db, params)
        except Exception as e:
            logger.error("[DB_CONDITIONS] Error ejecutando provider %s: %s", provider_key, e)
            value = None

        parts = provider_key.split(".")
        target = db_ctx
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value

        leaf["field"] = f"db.{provider_key}"

    context["db"] = db_ctx
    return context
