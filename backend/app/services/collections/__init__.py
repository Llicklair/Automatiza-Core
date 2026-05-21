"""Servicios de inteligencia de cobros (F3.9).

Dos motores complementarios:

  - `risk`       — Scoring de morosidad por cliente sobre histórico:
                    días-medios-cobro, ratio de impagos, importe vencido.
                    Sin ML — heurísticas robustas sobre datos del ERP.
                    Si más adelante hay >500 facturas/cliente con etiqueta
                    payment_date, se puede entrenar logistic regression.

  - `reminders`  — Calendario escalonado de recordatorios por factura:
                    aviso amable D-3, vencimiento D+0, requerimiento D+15,
                    requerimiento formal D+30 con intereses de demora.
"""

from app.services.collections.reminders import (
    ReminderStep,
    build_reminder_schedule,
    invoices_due_for_reminder,
)
from app.services.collections.risk import (
    ClientRiskScore,
    compute_client_risk,
    rank_tenant_collections,
)

__all__ = [
    "ClientRiskScore",
    "ReminderStep",
    "build_reminder_schedule",
    "compute_client_risk",
    "invoices_due_for_reminder",
    "rank_tenant_collections",
]
