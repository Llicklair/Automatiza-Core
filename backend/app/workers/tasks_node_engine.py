"""
Tareas del motor de nodos (workflows visuales con condicionales, delays, etc.).
Coroutines puras ejecutadas por TaskRunner.
"""

import asyncio
import logging

from app.services.idempotency import IdempotencyGuard

logger = logging.getLogger(__name__)


async def run_node_engine(execution_id: str, tenant_id: str | None = None):
    """Ejecuta un workflow via el motor de nodos (grafos con condicionales, delays, etc.).

    Fase 3 (RLS): `tenant_id` se recibe del dispatcher cuando es conocido,
    permitiendo fijar el ContextVar antes de la query de bootstrap. Si es
    None se hace fallback al tenant_id de la fila de WorkflowExecution.
    """
    guard = IdempotencyGuard()

    if await guard.already_executed("run_node_engine", execution_id):
        logger.info("[IDEMPOTENCY] run_node_engine:%s ya ejecutado. Skip.", execution_id)
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = await _run_node_engine(execution_id, tenant_id)
        await guard.mark_executed(
            "run_node_engine", execution_id, {"status": result.get("status", "unknown")}
        )
        return result
    except Exception as exc:
        logger.exception("Error en run_node_engine:%s", execution_id)
        if isinstance(exc, ConnectionError | OSError | TimeoutError):
            await guard.release("run_node_engine", execution_id)
            # Reintento simple con backoff
            for attempt in range(3):
                await asyncio.sleep(30 * (attempt + 1))
                try:
                    result = await _run_node_engine(execution_id, tenant_id)
                    await guard.mark_executed(
                        "run_node_engine", execution_id, {"status": result.get("status", "unknown")}
                    )
                    return result
                except Exception:
                    logger.debug(
                        "Reintento %d de run_node_engine:%s falló", attempt + 1, execution_id,
                        exc_info=True,
                    )
                    continue
        raise exc


async def resume_node_engine(execution_id: str, from_node_id: str, tenant_id: str | None = None):
    """Reanuda un workflow del motor de nodos tras delay o approval.

    Fase 3 (RLS): ver run_node_engine para la semántica de tenant_id.
    """
    guard = IdempotencyGuard()

    idempotency_key = f"{execution_id}:{from_node_id}"
    if await guard.already_executed("resume_node_engine", idempotency_key):
        logger.info("[IDEMPOTENCY] resume_node_engine:%s ya ejecutado. Skip.", idempotency_key)
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = await _resume_node_engine(execution_id, from_node_id, tenant_id)
        await guard.mark_executed(
            "resume_node_engine", idempotency_key, {"status": result.get("status", "unknown")}
        )
        return result
    except Exception as exc:
        logger.exception("Error en resume_node_engine:%s", idempotency_key)
        if isinstance(exc, ConnectionError | OSError | TimeoutError):
            await guard.release("resume_node_engine", idempotency_key)
            for attempt in range(3):
                await asyncio.sleep(10 * (attempt + 1))
                try:
                    result = await _resume_node_engine(execution_id, from_node_id, tenant_id)
                    await guard.mark_executed(
                        "resume_node_engine",
                        idempotency_key,
                        {"status": result.get("status", "unknown")},
                    )
                    return result
                except Exception:
                    logger.debug(
                        "Reintento %d de resume_node_engine:%s falló", attempt + 1, idempotency_key,
                        exc_info=True,
                    )
                    continue
        raise exc


async def _run_node_engine(execution_id: str, tenant_id: str | None = None):
    import uuid as _uuid

    from sqlalchemy import select

    from app.core.tenant_context import set_current_tenant
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import WorkflowExecution
    from app.services.ai.node_engine import NodeEngine

    # Fase 3 (RLS): fijar tenant_id en el ContextVar ANTES de la query de
    # bootstrap si el dispatcher lo conoce, para que RLS también cubra esta SELECT.
    if tenant_id:
        set_current_tenant(tenant_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == _uuid.UUID(execution_id))
        )
        execution = result.scalar_one_or_none()
        if not execution:
            return {"status": "failed", "error": "Execution not found"}

        # Defensa en profundidad: reafirmamos con el tenant real de la fila
        # (cubre el caso en que el dispatcher no haya propagado tenant_id).
        resolved_tenant = str(execution.tenant_id)
        set_current_tenant(resolved_tenant)

        engine = NodeEngine(
            workflow_id=str(execution.workflow_id),
            execution_id=execution_id,
            tenant_id=resolved_tenant,
            user_id=None,
            trigger_payload=execution.trigger_payload,
        )
        return await engine.run(db)


async def _resume_node_engine(execution_id: str, from_node_id: str, tenant_id: str | None = None):
    import uuid as _uuid

    from sqlalchemy import select

    from app.core.tenant_context import set_current_tenant
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import WorkflowExecution
    from app.services.ai.node_engine import NodeEngine

    # Fase 3 (RLS): ver _run_node_engine.
    if tenant_id:
        set_current_tenant(tenant_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == _uuid.UUID(execution_id))
        )
        execution = result.scalar_one_or_none()
        if not execution:
            return {"status": "failed", "error": "Execution not found"}

        resolved_tenant = str(execution.tenant_id)
        set_current_tenant(resolved_tenant)

        engine = NodeEngine(
            workflow_id=str(execution.workflow_id),
            execution_id=execution_id,
            tenant_id=resolved_tenant,
            user_id=None,
            trigger_payload=execution.trigger_payload,
        )
        return await engine.resume(db, from_node_id)
