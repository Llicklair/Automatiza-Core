"""
Tareas Celery del motor de nodos (workflows visuales con condicionales, delays, etc.).
"""
from app.workers.celery_app import celery_app, run_async


@celery_app.task(name="run_node_engine", bind=True, max_retries=3, time_limit=600, soft_time_limit=540)
def run_node_engine(self, execution_id: str):
    """Ejecuta un workflow vía el motor de nodos (grafos con condicionales, delays, etc.)."""
    from app.services.idempotency import SyncIdempotencyGuard
    guard = SyncIdempotencyGuard()

    if guard.already_executed("run_node_engine", execution_id):
        print(f"[IDEMPOTENCY] run_node_engine:{execution_id} ya ejecutado. Skip.")
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = run_async(_run_node_engine(execution_id))
        guard.mark_executed("run_node_engine", execution_id, {"status": result.get("status", "unknown")})
        return result
    except Exception as exc:
        import traceback
        traceback.print_exc()
        if isinstance(exc, (ConnectionError, OSError, TimeoutError)):
            guard.release("run_node_engine", execution_id)
            raise self.retry(exc=exc, countdown=30)
        raise exc


@celery_app.task(name="resume_node_engine", bind=True, max_retries=3, time_limit=600, soft_time_limit=540)
def resume_node_engine(self, execution_id: str, from_node_id: str):
    """Reanuda un workflow del motor de nodos tras delay o approval."""
    from app.services.idempotency import SyncIdempotencyGuard
    guard = SyncIdempotencyGuard()

    idempotency_key = f"{execution_id}:{from_node_id}"
    if guard.already_executed("resume_node_engine", idempotency_key):
        print(f"[IDEMPOTENCY] resume_node_engine:{idempotency_key} ya ejecutado. Skip.")
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = run_async(_resume_node_engine(execution_id, from_node_id))
        guard.mark_executed("resume_node_engine", idempotency_key, {"status": result.get("status", "unknown")})
        return result
    except Exception as exc:
        import traceback
        traceback.print_exc()
        if isinstance(exc, (ConnectionError, OSError, TimeoutError)):
            guard.release("resume_node_engine", idempotency_key)
            raise self.retry(exc=exc, countdown=10)
        raise exc


async def _run_node_engine(execution_id: str):
    import uuid as _uuid
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import WorkflowExecution
    from app.services.node_engine import NodeEngine

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == _uuid.UUID(execution_id))
        )
        execution = result.scalar_one_or_none()
        if not execution:
            return {"status": "failed", "error": "Execution not found"}

        engine = NodeEngine(
            workflow_id=str(execution.workflow_id),
            execution_id=execution_id,
            tenant_id=str(execution.tenant_id),
            user_id=None,
            trigger_payload=execution.trigger_payload,
        )
        return await engine.run(db)


async def _resume_node_engine(execution_id: str, from_node_id: str):
    import uuid as _uuid
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import WorkflowExecution
    from app.services.node_engine import NodeEngine

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == _uuid.UUID(execution_id))
        )
        execution = result.scalar_one_or_none()
        if not execution:
            return {"status": "failed", "error": "Execution not found"}

        engine = NodeEngine(
            workflow_id=str(execution.workflow_id),
            execution_id=execution_id,
            tenant_id=str(execution.tenant_id),
            user_id=None,
            trigger_payload=execution.trigger_payload,
        )
        return await engine.resume(db, from_node_id)
