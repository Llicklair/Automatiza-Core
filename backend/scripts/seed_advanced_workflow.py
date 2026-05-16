"""
Seed: AutomatizaciÃ³n compleja de ejemplo con todos los tipos de nodo.

Uso:
    cd backend
    python -m scripts.seed_advanced_workflow

O directamente:
    cd backend && python ../scripts/seed_advanced_workflow.py

Crea un workflow con el siguiente grafo:

    [Trigger: Manual]
         â”‚
    [Skill: billing]  â”€â”€  "Generar factura mensual para ACME"
         â”‚
    [Conditional]  â”€â”€  Â¿factura > 1000â‚¬?
        / \
      SÃ­    No
      â”‚      â”‚
  [Skill:  [Skill:
   email]   documents]
   â”‚         â”‚
   â””â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”˜
        â”‚
    [Delay 15s]
        â”‚
    [Approval Gate]  â”€â”€  "Aprobar envÃ­o al cliente"
        â”‚
    [Skill: email]  â”€â”€  "Enviar factura por email al cliente"

"""
import asyncio
import os
import sys

# Ajustar path para importar desde backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.chdir(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.db.base import AsyncSessionLocal  # noqa: E402
from app.db.models.models import Workflow  # noqa: E402
from sqlalchemy import select  # noqa: E402

WORKFLOW_NAME = "[DEMO] FacturaciÃ³n avanzada ACME con aprobaciÃ³n"

# â”€â”€â”€ Nodos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

NODES = [
    {
        "id": "trigger-1",
        "type": "trigger",
        "position": {"x": 300, "y": 0},
        "data": {
            "label": "Inicio manual",
            "trigger_type": "manual",
        },
    },
    {
        "id": "skill-billing",
        "type": "skill",
        "position": {"x": 300, "y": 120},
        "data": {
            "label": "Generar factura mensual ACME",
            "domain": "billing",
            "instruction": "Crea una factura para el cliente ACME Corp (NIF: A12345678) del mes actual por los servicios de consultorÃ­a prestados. Base imponible 1500â‚¬, IVA 21%.",
        },
    },
    {
        "id": "cond-amount",
        "type": "conditional",
        "position": {"x": 300, "y": 260},
        "data": {
            "label": "Â¿Importe > 1000â‚¬?",
            "condition": {
                "field": "skill-billing.output.extracted_data.amount_total",
                "operator": "gt",
                "value": 1000,
            },
        },
    },
    {
        "id": "skill-email-notify",
        "type": "skill",
        "position": {"x": 100, "y": 400},
        "data": {
            "label": "Notificar al director financiero",
            "domain": "email",
            "instruction": "EnvÃ­a un email al director financiero informando que se ha generado una factura de alto importe para ACME.",
        },
    },
    {
        "id": "skill-doc-archive",
        "type": "skill",
        "position": {"x": 500, "y": 400},
        "data": {
            "label": "Archivar como factura menor",
            "domain": "documents",
            "instruction": "Archiva la factura generada en la carpeta de facturas menores sin notificaciÃ³n especial.",
        },
    },
    {
        "id": "delay-review",
        "type": "delay",
        "position": {"x": 300, "y": 540},
        "data": {
            "label": "Esperar 15s para revisiÃ³n",
            "delay_seconds": 15,
        },
    },
    {
        "id": "approval-send",
        "type": "approval_gate",
        "position": {"x": 300, "y": 660},
        "data": {
            "label": "Aprobar envÃ­o al cliente",
            "description": "La factura de ACME estÃ¡ lista. Â¿Deseas enviarla al cliente por email?",
        },
    },
    {
        "id": "skill-email-final",
        "type": "skill",
        "position": {"x": 300, "y": 800},
        "data": {
            "label": "Enviar factura al cliente",
            "domain": "email",
            "instruction": "EnvÃ­a la factura generada por email al cliente ACME con un mensaje cordial adjuntando el PDF.",
        },
    },
]

# â”€â”€â”€ Aristas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

EDGES = [
    {
        "id": "e-trigger-billing",
        "source": "trigger-1",
        "target": "skill-billing",
        "type": "smoothstep",
    },
    {
        "id": "e-billing-cond",
        "source": "skill-billing",
        "target": "cond-amount",
        "type": "smoothstep",
    },
    {
        "id": "e-cond-email",
        "source": "cond-amount",
        "target": "skill-email-notify",
        "type": "smoothstep",
        "sourceHandle": "true",
        "data": {"branch": "true"},
    },
    {
        "id": "e-cond-doc",
        "source": "cond-amount",
        "target": "skill-doc-archive",
        "type": "smoothstep",
        "sourceHandle": "false",
        "data": {"branch": "false"},
    },
    {
        "id": "e-email-delay",
        "source": "skill-email-notify",
        "target": "delay-review",
        "type": "smoothstep",
    },
    {
        "id": "e-doc-delay",
        "source": "skill-doc-archive",
        "target": "delay-review",
        "type": "smoothstep",
    },
    {
        "id": "e-delay-approval",
        "source": "delay-review",
        "target": "approval-send",
        "type": "smoothstep",
    },
    {
        "id": "e-approval-final",
        "source": "approval-send",
        "target": "skill-email-final",
        "type": "smoothstep",
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        # Buscar primer tenant disponible
        from app.db.models.models import Tenant, User
        tenant_res = await db.execute(select(Tenant).limit(1))
        tenant = tenant_res.scalar_one_or_none()
        if not tenant:
            print("ERROR: No hay tenants en la BD. Ejecuta primero el seed bÃ¡sico.")
            return

        user_res = await db.execute(select(User).where(User.tenant_id == tenant.id).limit(1))
        user = user_res.scalar_one_or_none()

        # Eliminar workflow demo anterior si existe
        existing = await db.execute(select(Workflow).where(Workflow.name == WORKFLOW_NAME))
        old = existing.scalar_one_or_none()
        if old:
            db.delete(old)
            await db.flush()
            print("  Workflow demo anterior eliminado.")

        wf = Workflow(
            tenant_id=tenant.id,
            created_by=user.id if user else None,
            name=WORKFLOW_NAME,
            description=(
                "AutomatizaciÃ³n completa: genera factura â†’ evalÃºa importe â†’ "
                "notifica o archiva â†’ delay â†’ aprobaciÃ³n humana â†’ envÃ­o final."
            ),
            is_active=True,
            trigger_type="manual",
            trigger_config={},
            action_type="ai_task",
            action_config={
                "instruction": "Ejecutar flujo completo de facturaciÃ³n ACME con aprobaciÃ³n.",
                "domain": "billing",
            },
            ui_nodes=NODES,
            ui_edges=EDGES,
        )
        db.add(wf)
        await db.commit()
        await db.refresh(wf)

        print("")
        print(f"  Workflow creado: {wf.name}")
        print(f"  ID:             {wf.id}")
        print(f"  Tenant:         {tenant.name} ({tenant.id})")
        print(f"  Nodos:          {len(NODES)}")
        print(f"  Aristas:        {len(EDGES)}")
        print("")
        print("  Tipos de nodo:")
        for n in NODES:
            print(f"    [{n['type']:15s}] {n['id']:25s} â†’ {n['data'].get('label', '')}")
        print("")
        print("  Abre la UI en /automatizaciones y busca:")
        print(f"    '{WORKFLOW_NAME}'")
        print("")
        print("  Pulsa el botÃ³n â–¶ para ejecutar y observa el grafo en tiempo real.")


if __name__ == "__main__":
    print("=" * 70)
    print("  SEED: AutomatizaciÃ³n avanzada de demo")
    print("=" * 70)
    asyncio.run(seed())
    print("  Done!")
