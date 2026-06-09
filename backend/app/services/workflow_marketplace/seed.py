"""Seed de plantillas oficiales del marketplace (F3.10).

Idempotente: vuelve a llamar al seed no duplica filas (chequea por slug).
Las plantillas oficiales cubren los workflows recurrentes más útiles
para una pyme española:

  - `gestoria-mensual`     — recordatorio modelos AEAT + cuadre banca
  - `cierre-trimestral`    — cierre periodo + libros + 303 + 130
  - `recordatorios-cobros` — recordatorios escalonados (F3.9)
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workflow_template import WorkflowTemplate

_OFFICIAL_TEMPLATES: list[dict] = [
    {
        "slug": "gestoria-mensual",
        "name": "Gestoría mensual",
        "description": (
            "Cada mes, día 1: revisa la bandeja de facturas recibidas, "
            "lanza el cuadre bancario y avisa de vencimientos AEAT."
        ),
        "category": "fiscal",
        "author": "AutomatizaCore",
        "trigger_type": "cron",
        "trigger_config": {"cron": "0 9 1 * *"},
        "action_type": "agent_sequence",
        "action_config": {"agents": ["documents", "banking", "compliance"]},
        "execution_mode": "deterministic",
        "compiled_steps": [
            {"step": "list_received_invoices_pending", "agent": "documents"},
            {"step": "auto_reconcile", "agent": "banking"},
            {"step": "check_fiscal_deadlines", "agent": "compliance"},
        ],
        "tags": ["mensual", "fiscal", "gestoria"],
    },
    {
        "slug": "cierre-trimestral",
        "name": "Cierre trimestral",
        "description": (
            "Cierre del trimestre: cuadre contable, generación 303 + 130 + libros "
            "oficiales y aviso al usuario para revisar antes de presentar."
        ),
        "category": "fiscal",
        "author": "AutomatizaCore",
        "trigger_type": "cron",
        "trigger_config": {"cron": "0 9 1 1,4,7,10 *"},  # día 1 de Ene/Abr/Jul/Oct
        "action_type": "agent_sequence",
        "action_config": {"agents": ["accounting", "compliance"]},
        "execution_mode": "deterministic",
        "compiled_steps": [
            {"step": "close_period", "agent": "accounting"},
            {"step": "check_quarter_preventive", "agent": "compliance"},
            {"step": "build_modelo_303", "agent": "compliance"},
        ],
        "tags": ["trimestral", "fiscal", "303", "130"],
    },
    {
        "slug": "recordatorios-cobros",
        "name": "Recordatorios de cobro escalonados",
        "description": (
            "Cada mañana revisa las facturas y dispara los recordatorios "
            "amistosos, recordatorios de vencimiento y requerimientos formales "
            "según el calendario D-3 / D+0 / D+15 / D+30."
        ),
        "category": "cobros",
        "author": "AutomatizaCore",
        "trigger_type": "cron",
        "trigger_config": {"cron": "0 9 * * *"},
        "action_type": "agent_sequence",
        "action_config": {"agents": ["billing", "email"]},
        "execution_mode": "deterministic",
        "compiled_steps": [
            {"step": "invoices_due_for_reminder", "agent": "billing"},
            {"step": "send_reminders", "agent": "email"},
        ],
        "tags": ["cobros", "diario", "morosidad"],
    },
]


async def seed_official_templates(db: AsyncSession) -> dict:
    """Inserta las plantillas oficiales que falten. Devuelve recuento."""
    existing_q = await db.execute(sa.select(WorkflowTemplate.slug))
    existing_slugs = {row[0] for row in existing_q.all()}

    created = 0
    for spec in _OFFICIAL_TEMPLATES:
        if spec["slug"] in existing_slugs:
            continue
        db.add(
            WorkflowTemplate(
                slug=spec["slug"],
                name=spec["name"],
                description=spec.get("description"),
                category=spec["category"],
                author=spec.get("author"),
                trigger_type=spec["trigger_type"],
                trigger_config=spec.get("trigger_config", {}),
                action_type=spec["action_type"],
                action_config=spec.get("action_config", {}),
                execution_mode=spec.get("execution_mode", "reasoning"),
                compiled_steps=spec.get("compiled_steps"),
                tags=spec.get("tags") or [],
                is_official=True,
            )
        )
        created += 1
    if created:
        await db.commit()
    return {"created": created, "total_official": len(_OFFICIAL_TEMPLATES)}
