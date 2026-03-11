import asyncio
from sqlalchemy import select, desc
from app.db.base import AsyncSessionLocal
from app.db.models.models import Task, AuditLog

async def list_recent_tasks():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Task).order_by(desc(Task.created_at)).limit(3))
        tasks = res.scalars().all()
        print("=== ULTIMAS 3 TAREAS ===")
        for t in tasks:
            print(f"ID: {t.id} | Status: {t.status} | Intent: {t.user_intent}")
            print(f"Error: {t.error_message}")
            print(f"Results len: {len(t.agent_results) if t.agent_results else 0}")
            print("-" * 40)
            
            # Print audit logs for this task
            audit_res = await db.execute(
                select(AuditLog).where(AuditLog.task_id == t.id).order_by(AuditLog.executed_at)
            )
            audits = audit_res.scalars().all()
            if audits:
                print("Auditoría:")
                for a in audits:
                    print(f"  - Agent: {a.agent_name} | Action: {a.action_type} | Status: {a.status} | Error: {a.error_detail}")
            print("=" * 40)

if __name__ == "__main__":
    asyncio.run(list_recent_tasks())
