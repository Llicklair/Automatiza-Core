"""Conteo del "contrato" de capacidades del AIEmployee custom (uso advisory).

NOTA (2026-06-18): el alta de un custom YA NO exige ≥2 capacidades — un custom
"fino" (solo `system_prompt`) es válido. Estas funciones se conservan como
utilidad para AUDITAR qué customs son finos
(`scripts/audit_aiemployees_contract.py`); NO se invocan en el alta. El guard
defensivo de routing reimplementa su propio conteo en el classifier
(`_meets_employee_contract`), independiente de este módulo.

Capacidades contadas:
    scope             — filtro JSONB no vacío
    memory_enabled    — bool True
    knowledge_enabled — bool True
    workflows         — lista no vacía
"""

from __future__ import annotations

MIN_CAPABILITIES = 2


def _scope_present(scope: dict | None) -> bool:
    return bool(scope) and any(scope.values())


def _workflows_present(workflows: list | None) -> bool:
    return bool(workflows)


def count_capabilities(
    *,
    scope: dict | None,
    memory_enabled: bool,
    knowledge_enabled: bool,
    workflows: list | None,
) -> int:
    flags = (
        _scope_present(scope),
        bool(memory_enabled),
        bool(knowledge_enabled),
        _workflows_present(workflows),
    )
    return sum(flags)


def validate_employee_contract(
    *,
    scope: dict | None,
    memory_enabled: bool,
    knowledge_enabled: bool,
    workflows: list | None,
) -> tuple[bool, str]:
    """Devuelve (ok, message). Utilidad de AUDITORÍA — ya no bloquea el alta.

    ok=True  → el custom declara ≥2 capacidades.
    ok=False → el custom es "fino" (0-1 capacidades); útil para reportar, no
               para rechazar (el alta siempre se permite).
    """
    n = count_capabilities(
        scope=scope,
        memory_enabled=memory_enabled,
        knowledge_enabled=knowledge_enabled,
        workflows=workflows,
    )
    if n >= MIN_CAPABILITIES:
        return True, f"Contrato cumplido: {n}/4 capacidades."
    return (
        False,
        (
            f"El empleado custom debe declarar al menos {MIN_CAPABILITIES} de 4 "
            f"capacidades (actual: {n}). Activa scope/memoria/knowledge/workflows "
            f"o crea un 'Perfil' (solo system prompt) en lugar de un empleado."
        ),
    )
