"""Catálogo de eventos de negocio del event bus.

Única fuente de verdad de los nombres de evento que se emiten vía
`services/event_bus.emit_event`. Los Workflows event_based escuchan estos
nombres en `trigger_config["events"]` (o "any" como comodín).

Usar SIEMPRE estas constantes al emitir o al seedear rutinas — un typo en el
nombre rompe el trigger en silencio.
"""

from __future__ import annotations

# ── Facturación ──────────────────────────────────────────────────────────────
INVOICE_CREATED = "invoice_created"  # {invoice_id, invoice_number, amount_total, client_name}
INVOICE_PAID = "invoice_paid"  # {invoice_id, invoice_number}
INVOICE_OVERDUE = "invoice_overdue"  # {invoice_id, invoice_number, days_overdue}

# ── CRM / RRHH ───────────────────────────────────────────────────────────────
CLIENT_CREATED = "client_created"  # {client_id, name}
EMPLOYEE_CREATED = "employee_created"  # {employee_id, name}
PAYROLL_CREATED = "payroll_created"  # {payroll_id, employee_id}
PAYROLLS_BULK_CREATED = "payrolls_bulk_created"  # {count, month, year}
PAYROLLS_APPROVED = "payrolls_approved"  # {count, month, year}

# ── Documentos ───────────────────────────────────────────────────────────────
DOCUMENT_PROCESSED = "document_processed"  # {document_id, doc_type}

# ── Banca / conciliación ─────────────────────────────────────────────────────
BANKING_AUTO_RECONCILED = "banking_auto_reconciled"  # {count}
N43_IMPORTED = "n43_imported"  # {imported, skipped, reconciled, unmatched}
RECONCILIATION_EXCEPTIONS = "reconciliation_exceptions"  # {unmatched, total, source}

# ── Calendario ───────────────────────────────────────────────────────────────
MONTH_END = "month_end"  # {month, year} — mes RECIÉN CERRADO (emitido el día 1)

ALL_EVENTS: frozenset[str] = frozenset(
    v for k, v in globals().items() if k.isupper() and isinstance(v, str)
)
