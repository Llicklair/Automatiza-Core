"""
Evaluador de condiciones para workflows.

Las condiciones se almacenan en trigger_config["conditions"] con este schema:

  Condición hoja:
    {"field": "amount", "op": "gt", "value": 1000}

  Condición compuesta:
    {"operator": "AND", "conditions": [...]}
    {"operator": "OR",  "conditions": [...]}
    {"operator": "NOT", "condition": {...}}

Operadores soportados: eq, ne, gt, gte, lt, lte, contains, in, exists, not_exists

Uso:
    from app.services.workflow.conditions import evaluate_conditions
    if not evaluate_conditions(wf.trigger_config.get("conditions"), context):
        continue  # condición no cumplida, no disparar
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_field(context: dict, field: str) -> Any:
    """Accede a campos anidados con notación dot: 'invoice.amount'."""
    parts = field.split(".")
    val: Any = context
    for part in parts:
        if not isinstance(val, dict):
            return None
        val = val.get(part)
    return val


def _eval_leaf(condition: dict, context: dict) -> bool:
    field = condition.get("field", "")
    op = condition.get("op", "eq")
    expected = condition.get("value")
    actual = _get_field(context, field)

    try:
        match op:
            case "eq":
                return actual == expected
            case "ne":
                return actual != expected
            case "gt":
                return actual is not None and float(actual) > float(expected)
            case "gte":
                return actual is not None and float(actual) >= float(expected)
            case "lt":
                return actual is not None and float(actual) < float(expected)
            case "lte":
                return actual is not None and float(actual) <= float(expected)
            case "contains":
                return expected in str(actual) if actual is not None else False
            case "in":
                return actual in expected if isinstance(expected, list) else False
            case "exists":
                return actual is not None
            case "not_exists":
                return actual is None
            case _:
                logger.warning("[CONDITIONS] Operador desconocido: %s", op)
                return False
    except (TypeError, ValueError) as e:
        logger.warning("[CONDITIONS] Error evaluando %s %s %s: %s", field, op, expected, e)
        return False


def evaluate_conditions(condition: dict | None, context: dict) -> bool:
    """
    Evalúa una condición (hoja o compuesta) contra un context dict.
    Retorna True si no hay condición (no bloquea el disparo).
    """
    if not condition:
        return True

    operator = condition.get("operator", "").upper()

    if operator == "AND":
        return all(evaluate_conditions(c, context) for c in condition.get("conditions", []))

    if operator == "OR":
        return any(evaluate_conditions(c, context) for c in condition.get("conditions", []))

    if operator == "NOT":
        inner = condition.get("condition")
        if not inner:
            logger.warning("[CONDITIONS] Operador NOT sin condición interna; no se dispara (fail-closed)")
            return False
        return not evaluate_conditions(inner, context)

    # Condición hoja
    return _eval_leaf(condition, context)
