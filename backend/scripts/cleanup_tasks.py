import asyncio
from sqlalchemy import select, update
from app.db.base import AsyncSessionLocal
from app.db.models.models import Task, WorkflowExecution

async def cleanup():
    async with AsyncSessionLocal() as db:
        print("Marcando tareas en 'executing' como 'failed'...")
        await db.execute(
            update(Task)
            .where(Task.status == 'executing')
            .values(status='failed', error_message='Timeout por bloqueo del LLM (cancelado manualmente por mantenimiento)')
        )
        
        print("Marcando workflows en 'running' como 'failed'...")
        await db.execute(
            update(WorkflowExecution)
            .where(WorkflowExecution.status == 'running')
            .values(status='failed', result_log='Ejecución cancelada por tiempo de espera excedido.')
        )
        
        await db.commit()
        print("Limpieza completada exitosamente.")

if __name__ == "__main__":
    asyncio.run(cleanup())
