import asyncio
import json
from sqlalchemy import select
from app.db.base import AsyncSessionLocal
from app.db.models.models import Task

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Task)
            .where(Task.id == "0ed1e867-8db3-446d-bc8e-f7d17e41750d")
        )
        task = res.scalar_one_or_none()
        
        if task and task.agent_results:
            for idx, r in enumerate(task.agent_results):
                print(f"--- Agent Result {idx + 1} ---")
                print(json.dumps(r, indent=2))
                
if __name__ == "__main__":
    asyncio.run(run())
