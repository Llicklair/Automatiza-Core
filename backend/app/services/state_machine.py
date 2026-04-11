"""
Máquinas de estado para entidades críticas del sistema.

Define las transiciones válidas entre estados y lanza
InvalidTransitionError si se intenta una transición ilegal.

Principio: es mejor lanzar un error explícito que dejar
que una entidad quede en un estado incoherente.

Entidades cubiertas:
  - Invoice
  - Payroll
  - WorkflowExecution
  - PendingApproval
  - Task
"""

from __future__ import annotations


class InvalidTransitionError(ValueError):
    """Se lanza cuando se intenta una transición de estado no permitida."""

    def __init__(self, entity: str, current: str, target: str):
        super().__init__(
            f"[{entity}] Transición inválida: '{current}' → '{target}'. "
            f"Estados permitidos desde '{current}': {_ALLOWED[entity].get(current, [])}"
        )
        self.entity = entity
        self.current = current
        self.target = target


# ─── Mapa de transiciones permitidas ─────────────────────────────────────────
#
# Formato: { entity: { estado_origen: [estados_destino_permitidos] } }
#
# Regla: si el estado_origen no aparece en el mapa, la entidad está en
# un estado terminal (no se puede transicionar desde él).

_ALLOWED: dict[str, dict[str, list[str]]] = {
    # ── Invoice ──────────────────────────────────────────────────────────────
    # draft  → (se puede emitir o cancelar sin emitir)
    # issued → (se puede cobrar o cancelar)
    # paid   → TERMINAL (no se puede deshacer)
    # cancelled → TERMINAL
    "Invoice": {
        "draft": ["issued", "cancelled"],
        "issued": ["paid", "cancelled"],
        # paid y cancelled son terminales → no aparecen
    },
    # ── Payroll ──────────────────────────────────────────────────────────────
    # draft    → aprobada por el responsable de RRHH
    # approved → pagada al empleado
    # paid     → TERMINAL
    # rejected → TERMINAL (vuelve a draft si se corrige se crea una nueva)
    "Payroll": {
        "draft": ["approved", "rejected"],
        "approved": ["paid", "rejected"],
    },
    # ── WorkflowExecution ────────────────────────────────────────────────────
    # pending → running al iniciar ejecución
    # running → success | failed | paused al terminar o pausar
    # paused → running | failed al reanudar
    # success / failed → TERMINAL
    "WorkflowExecution": {
        "pending": ["running"],
        "running": ["success", "failed", "paused"],
        "paused": ["running", "failed"],
    },
    # ── PendingApproval ──────────────────────────────────────────────────────
    # pending → approved | rejected | expired
    "PendingApproval": {
        "pending": ["approved", "rejected", "expired"],
    },
    # ── Task ─────────────────────────────────────────────────────────────────
    # pending → planning | executing | cancelled
    # planning → executing | failed | cancelled
    # executing → done | failed | awaiting_approval | cancelled
    # awaiting_approval → executing | cancelled
    # done / failed / cancelled → TERMINAL
    "Task": {
        "pending": ["planning", "executing", "cancelled"],
        "planning": ["executing", "failed", "cancelled"],
        "executing": ["done", "failed", "awaiting_approval", "cancelled"],
        "awaiting_approval": ["executing", "cancelled"],
    },
    # ── Quote ────────────────────────────────────────────────────────────────
    "Quote": {
        "draft": ["sent", "cancelled"],
        "sent": ["accepted", "rejected", "cancelled"],
    },
}


# ─── Función principal de validación ─────────────────────────────────────────


def validate_transition(entity: str, current_status: str, new_status: str) -> None:
    """
    Valida que la transición de estado sea permitida.
    Lanza InvalidTransitionError si no lo es.

    Args:
        entity:         Nombre de la entidad ("Invoice", "Payroll", etc.)
        current_status: Estado actual de la entidad
        new_status:     Estado al que se quiere transicionar

    Raises:
        InvalidTransitionError: Si la transición no está permitida
    """
    # Mismo estado → siempre permitido (idempotente)
    if current_status == new_status:
        return

    transitions = _ALLOWED.get(entity, {})
    allowed_next = transitions.get(current_status)

    if allowed_next is None:
        # El estado actual es un terminal o no está definido
        raise InvalidTransitionError(entity, current_status, new_status)

    if new_status not in allowed_next:
        raise InvalidTransitionError(entity, current_status, new_status)


def can_transition(entity: str, current_status: str, new_status: str) -> bool:
    """
    Versión booleana de validate_transition, sin lanzar excepción.
    Útil para comprobar en UI antes de mostrar botones de acción.
    """
    try:
        validate_transition(entity, current_status, new_status)
        return True
    except InvalidTransitionError:
        return False


def allowed_next_states(entity: str, current_status: str) -> list[str]:
    """
    Devuelve la lista de estados válidos desde el estado actual.
    Devuelve lista vacía si es un estado terminal.
    """
    return _ALLOWED.get(entity, {}).get(current_status, [])


def is_terminal(entity: str, status: str) -> bool:
    """Devuelve True si el estado es terminal (no puede transicionar a otro)."""
    return status not in _ALLOWED.get(entity, {})
