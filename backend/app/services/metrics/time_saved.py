"""Tiempo ahorrado por la IA — estimación a partir del AuditLog.

Cada acción exitosa registrada en `audit_log` equivale a X minutos que un
humano habría tardado en hacerla a mano. La tabla de minutos es una
estimación honesta y conservadora (mejor quedarse cortos que inflar la
cifra). El widget del centro de mando consume `time_saved_summary`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tasks import AuditLog

# Minutos estimados de trabajo manual equivalente por action_type.
# Conservador a propósito: la cifra del dashboard debe ser creíble.
MINUTES_BY_ACTION: dict[str, int] = {
    # Facturación / contabilidad
    "create_invoice": 8,
    "invoice_created": 8,
    "create_journal_entry": 10,
    "journal_entry_created": 10,
    "reconcile_transaction": 6,
    "banking_auto_reconciled": 6,
    "n43_imported": 15,
    # RRHH
    "payroll_created": 12,
    "payrolls_bulk_created": 30,
    "approve_payroll": 3,
    # Documentos / email
    "document_processed": 7,
    "send_email": 5,
    "email_sent": 5,
    # Fiscal (preparación, nunca presentación automática)
    "aeat_presentation_confirmed": 20,
    # Workflows / decisiones
    "approval_decision": 2,
    "ai_task": 10,
}

# Acciones de fontanería que no representan trabajo humano ahorrado.
EXCLUDED_ACTIONS: frozenset[str] = frozenset({
    "user_registered",
    "node_execution_failed",
})

DEFAULT_MINUTES = 5


async def time_saved_summary(
    db: AsyncSession, tenant_id: UUID, *, days: int = 30
) -> dict:
    """Resumen de tiempo ahorrado en los últimos `days` días.

    Devuelve total en minutos/horas y desglose por action_type, contando solo
    acciones con status='success'.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)
    res = await db.execute(
        select(AuditLog.action_type, func.count())
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.status == "success",
            AuditLog.executed_at >= cutoff,
        )
        .group_by(AuditLog.action_type)
    )

    total_minutes = 0
    total_actions = 0
    breakdown: list[dict] = []
    for action_type, count in res.all():
        if action_type in EXCLUDED_ACTIONS:
            continue
        minutes_each = MINUTES_BY_ACTION.get(action_type, DEFAULT_MINUTES)
        minutes = minutes_each * count
        total_minutes += minutes
        total_actions += count
        breakdown.append({
            "action_type": action_type,
            "count": count,
            "minutes_each": minutes_each,
            "minutes": minutes,
        })

    breakdown.sort(key=lambda b: b["minutes"], reverse=True)
    return {
        "days": days,
        "total_actions": total_actions,
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 1),
        "breakdown": breakdown,
    }
