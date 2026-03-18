"""
Crea tres workflows de demostración:
  1. [RAZONAMIENTO]   Cierre mensual inteligente  — billing + crm + email, multi-agente con IA
  2. [DETERMINISTA]   Facturación recurrente       — billing + email, pasos fijos sin LLM
  3. [PARALELO]       Análisis mensual paralelo    — billing + crm + hr en paralelo → email (join)

Uso:
    python scripts/create_demo_workflows.py
"""

import asyncio
from sqlalchemy import select
from app.db.base import AsyncSessionLocal
from app.db.models.models import Workflow, Tenant


# ─── Nodos UI compartidos ──────────────────────────────────────────────────────

def _nodes_reasoning():
    return [
        {"id": "n-trigger",    "type": "trigger", "position": {"x": 50,  "y": 180}, "data": {"label": "Día 28 de cada mes"}},
        {"id": "n-billing",    "type": "action",  "position": {"x": 280, "y": 60},  "data": {"label": "Agente Facturación"}},
        {"id": "n-crm",        "type": "action",  "position": {"x": 280, "y": 180}, "data": {"label": "Agente CRM"}},
        {"id": "n-email",      "type": "action",  "position": {"x": 280, "y": 300}, "data": {"label": "Agente Email"}},
        {"id": "n-final",      "type": "action",  "position": {"x": 510, "y": 180}, "data": {"label": "Informe ejecutivo"}},
    ]

def _edges_reasoning():
    return [
        {"id": "e1", "source": "n-trigger", "target": "n-billing"},
        {"id": "e2", "source": "n-trigger", "target": "n-crm"},
        {"id": "e3", "source": "n-trigger", "target": "n-email"},
        {"id": "e4", "source": "n-billing", "target": "n-final"},
        {"id": "e5", "source": "n-crm",     "target": "n-final"},
        {"id": "e6", "source": "n-email",   "target": "n-final"},
    ]

def _nodes_deterministic():
    return [
        {"id": "n-trigger",  "type": "trigger", "position": {"x": 50,  "y": 120}, "data": {"label": "Día 1 de cada mes"}},
        {"id": "n-billing",  "type": "action",  "position": {"x": 280, "y": 60},  "data": {"label": "Generar facturas recurrentes"}},
        {"id": "n-email",    "type": "action",  "position": {"x": 280, "y": 180}, "data": {"label": "Enviar PDF al cliente"}},
        {"id": "n-log",      "type": "action",  "position": {"x": 510, "y": 120}, "data": {"label": "Registrar en CRM"}},
    ]

def _edges_deterministic():
    return [
        {"id": "e1", "source": "n-trigger", "target": "n-billing"},
        {"id": "e2", "source": "n-billing", "target": "n-email"},
        {"id": "e3", "source": "n-email",   "target": "n-log"},
    ]


def _nodes_parallel():
    return [
        # Trigger
        {"id": "p-trigger", "type": "trigger", "position": {"x": 250, "y": 0},   "data": {"label": "Inicio Manual", "trigger_type": "manual"}},
        # Parallel branch nodes (fan-out)
        {"id": "p-billing", "type": "skill",   "position": {"x": 50,  "y": 150}, "data": {"label": "Agente Facturación", "domain": "billing",  "description": "Analiza facturas pendientes y KPIs de cobros del mes."}},
        {"id": "p-crm",     "type": "skill",   "position": {"x": 250, "y": 150}, "data": {"label": "Agente CRM",         "domain": "crm",      "description": "Revisa pipeline de ventas, oportunidades abiertas y clientes en riesgo."}},
        {"id": "p-hr",      "type": "skill",   "position": {"x": 450, "y": 150}, "data": {"label": "Agente RRHH",        "domain": "hr",       "description": "Calcula coste salarial del mes y resumen de nóminas procesadas."}},
        # Join node (email)
        {"id": "p-email",   "type": "skill",   "position": {"x": 250, "y": 310}, "data": {"label": "Informe por Email",  "domain": "email",    "description": "Consolida los análisis de facturación, CRM y RRHH y envía el informe ejecutivo al gerente."}},
    ]


def _edges_parallel():
    return [
        # Fan-out: trigger → 3 parallel branches
        {"id": "ep1", "source": "p-trigger", "target": "p-billing"},
        {"id": "ep2", "source": "p-trigger", "target": "p-crm"},
        {"id": "ep3", "source": "p-trigger", "target": "p-hr"},
        # Fan-in: all 3 → email (join/merge)
        {"id": "ep4", "source": "p-billing", "target": "p-email"},
        {"id": "ep5", "source": "p-crm",     "target": "p-email"},
        {"id": "ep6", "source": "p-hr",      "target": "p-email"},
    ]


# ─── Pasos compilados del workflow determinista ────────────────────────────────

COMPILED_STEPS_FACTURACION = [
    {
        "agent": "billing",
        "action": "generate_recurring_invoices",
        "params": {
            "intent": (
                "Genera todas las facturas recurrentes que vencen este mes. "
                "Para cada cliente con facturación recurrente activa, crea una factura con los "
                "conceptos y precios pactados. Estado inicial: draft. "
                "Devuelve la lista de facturas creadas con su ID y cliente."
            )
        },
    },
    {
        "agent": "email",
        "action": "send_invoice_pdfs",
        "params": {
            "intent": (
                "Envía por email el PDF de cada factura recurrente recién generada. "
                "Para cada factura del paso anterior: adjunta el PDF y envíalo al email "
                "del cliente correspondiente. Asunto: 'Factura [número] - [mes/año]'. "
                "Usa un tono profesional y cordial."
            )
        },
    },
    {
        "agent": "crm",
        "action": "log_billing_activity",
        "params": {
            "intent": (
                "Registra en el CRM una actividad de tipo 'facturación' para cada cliente "
                "al que se le ha enviado factura este mes. "
                "Nota: 'Factura recurrente enviada automáticamente - [fecha]'."
            )
        },
    },
]


# ─── Main ──────────────────────────────────────────────────────────────────────

async def main():
    async with AsyncSessionLocal() as db:
        # Obtener el primer tenant disponible
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalars().first()
        if not tenant:
            print("❌ No hay tenants en la BD. Ejecuta primero smoke_demo.py.")
            return

        print(f"✔ Tenant: {tenant.name} ({tenant.id})")

        # ── Workflow 1: Razonamiento multi-agente ──────────────────────────────
        wf_reasoning = Workflow(
            tenant_id=tenant.id,
            name="[DEMO] Cierre mensual inteligente",
            description=(
                "El día 28 de cada mes analiza el estado financiero completo: "
                "detecta facturas impagadas, identifica clientes en riesgo en el CRM, "
                "calcula el coste salarial del mes y genera un informe ejecutivo con "
                "recomendaciones. Envía el resumen por email al gerente."
            ),
            is_active=True,
            trigger_type="schedule_based",
            trigger_config={"cron": "0 9 28 * *", "description": "Día 28 a las 9:00"},
            action_type="create_task",
            action_config={
                "agent": "coordinator",
                "intent": (
                    "Realiza el cierre mensual inteligente de la empresa:\n"
                    "1. FACTURACIÓN: Lista todas las facturas pendientes de cobro con más de 15 días "
                    "de antigüedad. Calcula el total de impagados y clasifícalos por cliente y riesgo.\n"
                    "2. CRM: Para cada cliente con facturas impagadas, revisa su historial CRM. "
                    "Actualiza su estado de riesgo y registra una actividad de seguimiento.\n"
                    "3. EMAIL: Genera y envía un informe ejecutivo al gerente con: total facturado el mes, "
                    "total cobrado, total pendiente, clientes en riesgo y recomendaciones de acción.\n"
                    "Razona sobre los datos para priorizar correctamente los casos críticos."
                ),
            },
            execution_mode="reasoning",
            compiled_steps=None,
            ui_nodes=_nodes_reasoning(),
            ui_edges=_edges_reasoning(),
        )
        db.add(wf_reasoning)
        print("✔ Workflow RAZONAMIENTO creado: Cierre mensual inteligente")

        # ── Workflow 2: Determinista ───────────────────────────────────────────
        wf_deterministic = Workflow(
            tenant_id=tenant.id,
            name="[DEMO] Facturación recurrente mensual",
            description=(
                "El día 1 de cada mes genera automáticamente todas las facturas recurrentes "
                "activas, envía el PDF por email a cada cliente y registra la actividad en el CRM. "
                "Proceso completamente automático sin intervención de IA en cada ejecución."
            ),
            is_active=True,
            trigger_type="schedule_based",
            trigger_config={"cron": "0 8 1 * *", "description": "Día 1 a las 8:00"},
            action_type="create_task",
            action_config={
                "agent": "billing",
                "intent": "Generar facturas recurrentes mensuales y enviarlas a los clientes.",
            },
            execution_mode="deterministic",
            compiled_steps=COMPILED_STEPS_FACTURACION,
            ui_nodes=_nodes_deterministic(),
            ui_edges=_edges_deterministic(),
        )
        db.add(wf_deterministic)
        print("✔ Workflow DETERMINISTA creado: Facturación recurrente mensual")

        # ── Workflow 3: Paralelo (fan-out → fan-in) ───────────────────────────
        wf_parallel = Workflow(
            tenant_id=tenant.id,
            name="[DEMO] Análisis mensual paralelo",
            description=(
                "Lanza en paralelo tres agentes (Facturación, CRM y RRHH) para analizar "
                "el estado mensual de la empresa de forma simultánea. Cuando los tres finalizan, "
                "el agente de Email consolida los resultados y envía un informe ejecutivo al gerente. "
                "Demuestra la ejecución paralela de ramas con asyncio.gather."
            ),
            is_active=True,
            trigger_type="manual",
            trigger_config={},
            action_type="create_task",
            action_config={
                "agent": "coordinator",
                "instruction": (
                    "Realiza el análisis mensual paralelo de la empresa:\n"
                    "1. FACTURACIÓN (paralelo): Analiza facturas pendientes, KPIs de cobro y morosidad.\n"
                    "2. CRM (paralelo): Revisa pipeline de ventas, oportunidades y clientes en riesgo.\n"
                    "3. RRHH (paralelo): Calcula coste salarial, nóminas y resumen de plantilla.\n"
                    "4. EMAIL (tras los tres): Consolida los tres análisis en un informe ejecutivo "
                    "y envíalo al gerente con resumen de KPIs críticos y recomendaciones."
                ),
            },
            execution_mode="reasoning",
            compiled_steps=None,
            ui_nodes=_nodes_parallel(),
            ui_edges=_edges_parallel(),
        )
        db.add(wf_parallel)
        print("✔ Workflow PARALELO creado: Análisis mensual paralelo")

        await db.commit()

    print("\n✅ Workflows de demo creados. Vélos en http://localhost:3000/automatizaciones")
    print("\n  [RAZONAMIENTO]  Cierre mensual inteligente")
    print("    → Trigger: cron 0 9 28 * * (día 28 a las 9:00)")
    print("    → Agentes: coordinator → billing + crm + email")
    print("    → Coste:   LLM en cada ejecución (razona sobre datos reales del mes)")
    print("\n  [DETERMINISTA]  Facturación recurrente mensual")
    print("    → Trigger: cron 0 8 1 * * (día 1 a las 8:00)")
    print("    → Agentes: billing → email → crm (pasos fijos, sin LLM)")
    print("    → Coste:   0 tokens por ejecución")
    print("\n  [PARALELO]      Análisis mensual paralelo")
    print("    → Trigger: manual")
    print("    → Topología: trigger → [billing || crm || hr] → email (fan-out/fan-in)")
    print("    → Motor:   NodeEngine con asyncio.gather (ejecución paralela real)")
    print("    → Coste:   LLM en cada ejecución")


if __name__ == "__main__":
    asyncio.run(main())
