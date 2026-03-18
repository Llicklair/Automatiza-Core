"""
Tareas del motor de nodos (workflows visuales con condicionales, delays, etc.).
Coroutines puras ejecutadas por TaskRunner.
"""
import asyncio
import logging

from app.services.idempotency import IdempotencyGuard

logger = logging.getLogger(__name__)


async def run_node_engine(execution_id: str):
    """Ejecuta un workflow via el motor de nodos (grafos con condicionales, delays, etc.)."""
    guard = IdempotencyGuard()

    if await guard.already_executed("run_node_engine", execution_id):
        logger.info("[IDEMPOTENCY] run_node_engine:%s ya ejecutado. Skip.", execution_id)
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = await _run_node_engine(execution_id)
        await guard.mark_executed("run_node_engine", execution_id, {"status": result.get("status", "unknown")})
        return result
    except Exception as exc:
        import traceback
        traceback.print_exc()
        if isinstance(exc, (ConnectionError, OSError, TimeoutError)):
            await guard.release("run_node_engine", execution_id)
            # Reintento simple con backoff
            for attempt in range(3):
                await asyncio.sleep(30 * (attempt + 1))
                try:
                    result = await _run_node_engine(execution_id)
                    await guard.mark_executed("run_node_engine", execution_id, {"status": result.get("status", "unknown")})
                    return result
                except Exception:
                    continue
        raise exc


async def resume_node_engine(execution_id: str, from_node_id: str):
    """Reanuda un workflow del motor de nodos tras delay o approval."""
    guard = IdempotencyGuard()

    idempotency_key = f"{execution_id}:{from_node_id}"
    if await guard.already_executed("resume_node_engine", idempotency_key):
        logger.info("[IDEMPOTENCY] resume_node_engine:%s ya ejecutado. Skip.", idempotency_key)
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = await _resume_node_engine(execution_id, from_node_id)
        await guard.mark_executed("resume_node_engine", idempotency_key, {"status": result.get("status", "unknown")})
        return result
    except Exception as exc:
        import traceback
        traceback.print_exc()
        if isinstance(exc, (ConnectionError, OSError, TimeoutError)):
            await guard.release("resume_node_engine", idempotency_key)
            for attempt in range(3):
                await asyncio.sleep(10 * (attempt + 1))
                try:
                    result = await _resume_node_engine(execution_id, from_node_id)
                    await guard.mark_executed("resume_node_engine", idempotency_key, {"status": result.get("status", "unknown")})
                    return result
                except Exception:
                    continue
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
