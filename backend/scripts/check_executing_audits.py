import asyncio
from sqlalchemy import select
from app.db.base import AsyncSessionLocal
from app.db.models.models import Task, AuditLog

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Task).where(Task.status == 'executing'))
        tasks = res.scalars().all()
        print(f"=== TAREAS EN EJECUCION ({len(tasks)}) ===")
        for t in tasks:
            print(f"Task ID: {t.id} (Created: {t.created_at})")
            print(f"Intent: {t.user_intent}")
            print(f"Domain: {getattr(t, 'domain', 'N/A')}")
            
            # Fetch audits
            audit_res = await db.execute(select(AuditLog).where(AuditLog.task_id == t.id).order_by(AuditLog.executed_at))
            audits = audit_res.scalars().all()
            if audits:
                print("Audits:")
                for a in audits:
                    print(f"  [{a.executed_at}] {a.action_type} - {a.status} : {a.error_detail}")
            else:
                print("No audits.")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(check())
