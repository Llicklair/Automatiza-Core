"""Validación del contrato del AIEmployee custom.

Un AIEmployee custom debe aportar al menos **2 de 4 capacidades**
verificables para justificar existir como entidad propia frente a un
default + system_prompt addendum. Si no cumple → la UI degrada a "Perfil"
(lo que es esencialmente sólo un addendum de prompt).

Capacidades verificables:
    scope             — filtro JSONB no vacío
    memory_enabled    — bool True
    knowledge_enabled — bool True
    workflows         — lista no vacía

Decisión completa en [tasks/todo.md] §"Decisión arquitectónica 2026-05-20".
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
    """Devuelve (ok, message).

    ok=True  → el custom aporta valor real (≥2 capacidades).
    ok=False → el custom no se diferencia de un Perfil; la ruta debe
               responder 422 invitando al alta como "Perfil".
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
