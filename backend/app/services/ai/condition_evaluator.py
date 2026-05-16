"""
Evaluador seguro de condiciones para nodos condicionales del motor de nodos.

Soporta dot-path traversal sobre el contexto de ejecución.
No usa eval() — solo operadores predefinidos.

Ejemplo de condición:
    {"field": "node-2.success", "operator": "eq", "value": True}
    {"field": "prev.output.amount_total", "operator": "gt", "value": 1000}
"""

from __future__ import annotations

from typing import Any


def _resolve_field(field: str, context: dict) -> Any:
    """
    Resuelve un campo con dot-path traversal.

    Paths soportados:
        "node-2.success"          → context["node-2"]["success"]
        "prev.output.amount_total" → context["prev"]["output"]["amount_total"]
    """
    parts = field.split(".")
    current: Any = context
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def _coerce_numeric(value: Any) -> float | None:
    """Intenta convertir a float para comparaciones numéricas."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def evaluate_condition(condition: dict, context: dict) -> bool:
    """
    Evalúa una condición contra el contexto de ejecución.

    Args:
        condition: {"field": str, "operator": str, "value": Any}
        context: Diccionario con outputs de nodos previos.
                 Estructura: {"node-1": {"status": ..., "output": ...}, "prev": {...}}

    Returns:
        True si la condición se cumple, False en caso contrario.

    Operadores soportados:
        eq, neq, gt, lt, gte, lte, contains, exists, not_exists
    """
    field = condition.get("field", "")
    operator = condition.get("operator", "eq")
    expected = condition.get("value")

    resolved = _resolve_field(field, context)

    if operator == "exists":
        return resolved is not None

    if operator == "not_exists":
        return resolved is None

    if operator == "eq":
        return resolved == expected

    if operator == "neq":
        return resolved != expected

    if operator == "contains":
        if isinstance(resolved, str) and isinstance(expected, str):
            return expected in resolved
        if isinstance(resolved, list | tuple):
            return expected in resolved
        return False

    # Numeric comparisons
    resolved_num = _coerce_numeric(resolved)
    expected_num = _coerce_numeric(expected)

    if resolved_num is None or expected_num is None:
        return False

    if operator == "gt":
        return resolved_num > expected_num
    if operator == "lt":
        return resolved_num < expected_num
    if operator == "gte":
        return resolved_num >= expected_num
    if operator == "lte":
        return resolved_num <= expected_num

    return False
