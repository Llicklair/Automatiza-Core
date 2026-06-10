"""Rutinas de oficio — workflows event_based sembrados por defecto en cada tenant.

Son el "motor proactivo" de back-office: en vez de esperar órdenes, el sistema
reacciona a eventos del negocio (N43 importado, factura vencida, cierre de mes,
documento procesado). Cada rutina crea una Task que pasa por el orquestador y,
por tanto, por el autonomy gate: las acciones de escritura sensibles acaban en
la bandeja de aprobaciones (CONFIRM) según la política del tenant.

Seed idempotente por `routine_key` en `action_config` — re-ejecutar no duplica.
Se invoca en el alta de tenant (auth/service.register) y vía endpoint admin
para tenants existentes.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workflows import Workflow
from app.services import events_catalog as ev

logger = logging.getLogger(__name__)

# routine_key -> definición. Cambiar la instrucción aquí NO actualiza tenants
# ya sembrados (el workflow es editable por el usuario; no lo pisamos).
DEFAULT_ROUTINES: dict[str, dict] = {
    "reconciliation_exceptions_review": {
        "name": "Revisar excepciones de conciliación",
        "description": (
            "Cuando la conciliación automática deja movimientos bancarios sin "
            "casar, analiza cada uno, propone la factura o asiento más probable "
            "y envía las propuestas a la bandeja de aprobaciones."
        ),
        "events": [ev.RECONCILIATION_EXCEPTIONS],
        "domain": "banking",
        "instruction": (
            "Revisa los movimientos bancarios sin conciliar, busca facturas o "
            "asientos candidatos y propón la conciliación. No ejecutes "
            "escrituras sin aprobación."
        ),
    },
    "overdue_invoice_reminder": {
        "name": "Recordatorio de factura vencida",
        "description": (
            "Cuando una factura vence sin cobrar, prepara un email de "
            "recordatorio de pago al cliente y déjalo pendiente de aprobación."
        ),
        "events": [ev.INVOICE_OVERDUE],
        "domain": "email",
        "instruction": (
            "Prepara un email cordial de recordatorio de pago para la factura "
            "vencida indicada en el contexto, dirigido al cliente. Déjalo "
            "pendiente de aprobación antes de enviar."
        ),
    },
    "month_end_draft_close": {
        "name": "Cierre mensual en borrador",
        "description": (
            "El día 1 de cada mes, prepara un resumen del mes cerrado "
            "(facturación, cobros, gastos) y los asientos de cierre en "
            "borrador para revisión."
        ),
        "events": [ev.MONTH_END],
        "domain": "accounting",
        "instruction": (
            "Prepara el cierre del mes indicado en el contexto: resumen de "
            "facturación emitida y cobrada, gastos registrados y asientos de "
            "cierre en borrador. Todo queda pendiente de revisión humana."
        ),
    },
    "received_invoice_to_journal": {
        "name": "Contabilizar factura recibida",
        "description": (
            "Cuando se procesa un documento clasificado como factura recibida, "
            "propone el asiento contable correspondiente en borrador."
        ),
        "events": [ev.DOCUMENT_PROCESSED],
        "conditions": {"field": "document_type", "op": "contains", "value": "factura"},
        "domain": "accounting",
        "instruction": (
            "Se ha procesado un documento que parece una factura. Si es una "
            "factura recibida, propón el asiento contable en borrador con los "
            "datos extraídos. No contabilices sin aprobación."
        ),
    },
}


async def seed_default_routines(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> list[str]:
    """Siembra las rutinas de oficio que falten en el tenant. Devuelve las creadas.

    Idempotente por `action_config.routine_key`. No hace commit: el caller decide.
    """
    res = await db.execute(
        select(Workflow.action_config).where(
            Workflow.tenant_id == tenant_id,
            Workflow.trigger_type == "event_based",
        )
    )
    existing_keys = {
        (cfg or {}).get("routine_key")
        for (cfg,) in res.all()
    }

    created: list[str] = []
    for key, spec in DEFAULT_ROUTINES.items():
        if key in existing_keys:
            continue
        trigger_config: dict = {"events": spec["events"]}
        if spec.get("conditions"):
            trigger_config["conditions"] = spec["conditions"]
        db.add(
            Workflow(
                tenant_id=tenant_id,
                created_by=user_id,
                name=spec["name"],
                description=spec["description"],
                is_active=True,
                trigger_type="event_based",
                trigger_config=trigger_config,
                action_type="ai_task",
                action_config={
                    "instruction": spec["instruction"],
                    "domain": spec["domain"],
                    "routine_key": key,
                    "seeded": True,
                },
            )
        )
        created.append(key)

    if created:
        logger.info(
            "[ROUTINES] %d rutina(s) de oficio sembradas en tenant %s: %s",
            len(created), tenant_id, ", ".join(created),
        )
    return created
