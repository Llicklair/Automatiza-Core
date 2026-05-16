import sys

sys.path.insert(0, r"C:\Users\Marcos\Desktop\atomatizacion de empresas\backend")
import asyncio
import pprint

from app.db.base import AsyncSessionLocal
from app.db.models.models import Task, WorkflowExecution
from sqlalchemy import select


async def run():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Task).order_by(Task.created_at.desc()).limit(1))
        tasks = result.scalars().all()
        print("--- TASKS ---")
        pprint.pprint([{"id": str(t.id), "status": t.status, "error_message": t.error_message, "domain": t.domain} for t in tasks])

        w_result = await db.execute(select(WorkflowExecution).order_by(WorkflowExecution.started_at.desc()).limit(1))
        wfs = w_result.scalars().all()
        print("\n--- WORKFLOW EXECUTIONS ---")
        pprint.pprint([{"id": str(w.id), "status": w.status, "error": w.error} for w in wfs])
asyncio.run(run())
