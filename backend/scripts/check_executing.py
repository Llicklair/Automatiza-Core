import asyncio
from sqlalchemy import select
from app.db.base import AsyncSessionLocal
from app.db.models.models import Task, WorkflowExecution

async def check():
    async with AsyncSessionLocal() as db:
        print("=== TAREAS DEL COORDINADOR ===")
        res = await db.execute(select(Task).where(Task.domain == 'coordinator'))
        tasks = res.scalars().all()
        for t in tasks:
            print(f"ID: {t.id} | Intent: {getattr(t, 'user_intent', 'N/A')} | Status: {t.status}")
            print(f"Current Step: {getattr(t, 'current_step', 'N/A')}")
            print("-" * 40)

        print("\n=== WORKFLOWS EN EJECUCION ===")
        res_wf = await db.execute(select(WorkflowExecution).where(WorkflowExecution.status == 'running'))
        wfs = res_wf.scalars().all()
        for w in wfs:
            print(f"ID: {w.id} | Status: {w.status}")
            print(f"Result Log: {w.result_log}")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(check())
