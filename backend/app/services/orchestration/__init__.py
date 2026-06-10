"""Servicios de orquestación (capa Coordinador).

Lógica reusable extraída de `agents/orchestrator/` para que servicios
(node_engine) y dispatchers compartan una única fuente de verdad sin
violar capas (services no debe importar agents):

  context.py   — persistencia: documentos generados por IA, PendingApproval
  executor.py  — instrumentación de ejecución: errores, auditoría, broadcast WS
  summaries.py — formateo de resúmenes y extracción de fechas en español
"""

from app.services.orchestration.context import (
    ensure_pending_approval,
    lock_document,
    messages_already_generated_pdf,
    response_indicates_approval,
    save_ai_result_as_csv,
    save_ai_result_as_document,
    unlock_document,
)
from app.services.orchestration.executor import (
    audit_log_result,
    broadcast_progress,
    make_error_result,
    release_employee,
)
from app.services.orchestration.summaries import extract_month_year, format_summary

__all__ = [
    "audit_log_result",
    "broadcast_progress",
    "ensure_pending_approval",
    "extract_month_year",
    "format_summary",
    "lock_document",
    "make_error_result",
    "messages_already_generated_pdf",
    "release_employee",
    "response_indicates_approval",
    "save_ai_result_as_csv",
    "save_ai_result_as_document",
    "unlock_document",
]
