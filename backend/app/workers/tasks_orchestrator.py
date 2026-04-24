"""
Tareas del orquestador LangGraph.
Coroutines puras ejecutadas por TaskRunner.
"""

import asyncio
import logging

from app.db.base import AsyncSessionLocal
from app.services.exec_log_store import push as log_push
from app.services.idempotency import IdempotencyGuard
from app.workers._orchestrator_context import (
    _build_initial_state,
    _create_invoice_from_approval,
    _load_and_start_task,
    _load_task_and_approval,
    _stream_and_log,
)
from app.workers._orchestrator_state import (
    _mark_task_failed,
    _save_final_state,
    _sync_workflow_artifacts,
)

logger = logging.getLogger(__name__)


def _is_transient_error(exc: Exception) -> bool:
    """Devuelve True si el error es transitorio (red, timeout, rate limit)."""
    err_str = str(exc).lower()
    return isinstance(exc, (ConnectionError, OSError, TimeoutError)) or any(
        kw in err_str
        for kw in (
            "429",
            "rate limit",
            "timeout",
            "service unavailable",
            "overloaded",
            "connection",
        )
    )


async def _retry(label: str, task_id: str, fn, guard, *, attempts: int, backoff_base: int):
    """
    Ejecuta fn() con reintentos exponenciales.
    Marca la tarea como fallida y re-lanza si se agotan los intentos.
    """
    exc = None
    for attempt in range(attempts):
        countdown = backoff_base * (2**attempt)
        logger.warning(
            "[RETRY] %s:%s intento %d/%d en %ds", label, task_id, attempt + 1, attempts, countdown
        )
        await asyncio.sleep(countdown)
        try:
            result = await fn()
            await guard.mark_executed(label, task_id, {"status": "done"})
            return result
        except Exception as retry_exc:
            logger.warning(
                "[RETRY] %s:%s fallo intento %d: %s", label, task_id, attempt + 1, retry_exc
            )
            exc = retry_exc
    await _mark_task_failed(task_id, str(exc))
    raise exc


async def execute_orchestrator(task_id: str):
    """Ejecuta el orquestador LangGraph para una tarea dada."""
    guard = IdempotencyGuard()

    if await guard.already_executed("run_orchestrator", task_id):
        logger.info("[IDEMPOTENCY] run_orchestrator:%s ya ejecutado. Skip.", task_id)
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = await _execute_orchestrator(task_id)
        await guard.mark_executed("run_orchestrator", task_id, {"status": "done"})
        return result
    except Exception as exc:
        logger.exception("Error en run_orchestrator:%s", task_id)
        if _is_transient_error(exc):
            await guard.release("run_orchestrator", task_id)
            return await _retry(
                "run_orchestrator",
                task_id,
                lambda: _execute_orchestrator(task_id),
                guard,
                attempts=3,
                backoff_base=30,
            )
        await _mark_task_failed(task_id, str(exc))
        raise


async def resume_orchestrator(task_id: str):
    """Reanuda el orquestador tras una aprobacion humana."""
    guard = IdempotencyGuard()

    if await guard.already_executed("resume_orchestrator", task_id):
        logger.info("[IDEMPOTENCY] resume_orchestrator:%s ya ejecutado. Skip.", task_id)
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = await _resume_orchestrator(task_id)
        await guard.mark_executed("resume_orchestrator", task_id, {"status": "done"})
        return result
    except Exception:
        logger.exception("Error en resume_orchestrator:%s", task_id)
        await guard.release("resume_orchestrator", task_id)
        return await _retry(
            "resume_orchestrator",
            task_id,
            lambda: _resume_orchestrator(task_id),
            guard,
            attempts=3,
            backoff_base=10,
        )


async def _execute_orchestrator(task_id: str):
    """Coordina: cargar tarea -> construir estado -> stream LangGraph -> persistir."""
    from app.agents.orchestrator import orchestrator

    async with AsyncSessionLocal() as db:
        task = await _load_and_start_task(task_id, db)
        if not task:
            return

        initial_state = await _build_initial_state(task, task_id, db)

        log_push(task_id, "Iniciando automatizacion...")
        final_state = await _stream_and_log(task_id, initial_state, orchestrator)

        await _save_final_state(task, final_state, db)
        await _sync_workflow_artifacts(task, final_state, db)
        await db.commit()


async def _resume_orchestrator(task_id: str):
    """
    Reanuda la ejecucion despues de una aprobacion humana.
    Coordina: cargar tarea/approval -> crear factura -> re-invocar LangGraph.
    """
    from app.agents.orchestrator import OrchestratorState, TaskStatus, orchestrator

    async with AsyncSessionLocal() as db:
        result = await _load_task_and_approval(task_id, db)
        if not result:
            return
        task, payload_data = result

        ok = await _create_invoice_from_approval(task, payload_data, db)
        if not ok:
            return

        initial_state: OrchestratorState = {
            "task_id": task_id,
            "tenant_id": str(task.tenant_id),
            "user_id": str(task.created_by) if task.created_by else "",
            "user_intent": task.user_intent or "",
            "current_intent": None,
            "classified_domain": task.domain if task.domain else None,
            "plan": task.plan,
            "current_step": task.current_step,
            "agent_results": task.agent_results,
            "status": TaskStatus.EXECUTING,
            "requires_human_approval": False,
            "approval_id": None,
            "error_message": task.error_message,
            "iteration_count": 0,
            "tenant_knowledge": [],
            "additional_metadata": task.additional_metadata or {},
        }

        final_state = await orchestrator.ainvoke(initial_state, config={"recursion_limit": 50})

        await _save_final_state(task, final_state, db)
        await db.commit()
