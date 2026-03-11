import asyncio
import uuid
import datetime
from sqlalchemy import select
from app.db.base import AsyncSessionLocal
from app.db.models.models import Workflow, Tenant, WorkflowExecution

async def run():
    async with AsyncSessionLocal() as db:
        # 1. Get a valid tenant_id
        res_tenant = await db.execute(select(Tenant).limit(1))
        tenant = res_tenant.scalars().first()
        
        if not tenant:
            print("No tenants found.")
            return
            
        print(f"Using Tenant ID: {tenant.id}")

        # 2. Add an example Workflow if it doesn't exist
        res_wf = await db.execute(select(Workflow).where(Workflow.tenant_id == tenant.id))
        wfs = res_wf.scalars().all()
        
        if not wfs:
            print("No workflows found. Creating a test one...")
            wf = Workflow(
                tenant_id=tenant.id,
                name="[DEMO] Nueva Factura -> Email",
                description="Cuando se crea una factura, preparar un email al cliente.",
                is_active=True,
                trigger_type="event_based",
                trigger_config={"event": "invoice_created"},
                action_type="create_task",
                action_config={"agent": "email", "intent": "Genera un email para enviarle la factura recién creada al cliente."},
                ui_nodes=[
                    {"id": "node-1", "type": "trigger", "position": {"x": 100, "y": 100}, "data": {"label": "Factura Creada"}},
                    {"id": "node-2", "type": "action", "position": {"x": 400, "y": 100}, "data": {"label": "Enviar Email"}}
                ],
                ui_edges=[
                    {"source": "node-1", "target": "node-2", "id": "edge-1"}
                ]
            )
            db.add(wf)
            await db.commit()
            await db.refresh(wf)
            wfs = [wf]
        
        wf = wfs[0]
        print(f"--- Workflow ID: {wf.id} ---")
        print(f"Name: {wf.name}")
        print(f"Trigger: {wf.trigger_type} ({wf.trigger_config})")
        print(f"Action: {wf.action_type} ({wf.action_config})")
        
        # 3. Simulate an Event Trigger to test DeepSeek R1 
        print("\nFiring workflow manually to test DeepSeek graph execution...")
        
        # We simulate the exact logic from the workflows router to fire the orchestrator via celery
        from app.db.models.models import Task
        from app.workers.celery_app import run_orchestrator
        
        task = Task(
            tenant_id=tenant.id,
            domain="workflows",
            user_intent=f"[Regla Automática: {wf.name}] {wf.action_config.get('intent', '')}",
            status="pending",
            additional_metadata={"workflow_id": str(wf.id), "event": "manual_test"}
        )
        db.add(task)
        await db.flush()
        
        execution = WorkflowExecution(
            workflow_id=wf.id,
            tenant_id=tenant.id,
            task_id=task.id,
            status="running",
            trigger_payload={"source": "manual_test"}
        )
        db.add(execution)
        await db.commit()
        await db.refresh(task)
        print(f"Created Task ID: {task.id} for the workflow")
        
        run_orchestrator.delay(str(task.id))
        print("Celery task dispatched! Please wait for DeepSeek R1 to crunch through the workflow...")
        print(f"Check execution with Task ID: {task.id}")

if __name__ == "__main__":
    asyncio.run(run())
