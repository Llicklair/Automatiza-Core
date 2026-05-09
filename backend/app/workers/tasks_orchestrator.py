"""
Tareas del orquestador LangGraph.
Coroutines puras ejecutadas por TaskRunner.
"""

import asyncio
import logging

from app.core.tenant_context import set_current_task, set_current_tenant
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


async def _set_agent_status(db, employee_id: str, tenant_id: str, status: str) -> None:
    """Actualiza el status de un AIEmployee en la sesión actual."""
    import uuid as _uuid
    from sqlalchemy import select as _select
    from app.db.models.ai_employees import AIEmployee
    result = await db.execute(
        _select(AIEmployee).where(
            AIEmployee.id == _uuid.UUID(employee_id),
            AIEmployee.tenant_id == _uuid.UUID(tenant_id),
        )
    )
    emp = result.scalar_one_or_none()
    if emp:
        emp.status = status


async def _log_task_completion(db, task, final_state: dict, employee_id: str | None, tenant_id: str):
    """Crea entrada de actividad con el resultado del agente."""
    from app.services.workflow.activity import log_activity
    results = final_state.get("agent_results", [])
    error = final_state.get("error_message")
    if error:
        message, icon = f"Error: {str(error)[:150]}", "❌"
    elif results:
        last = results[-1]
        raw = last.get("output") or last.get("summary") or last.get("result") or ""
        message = str(raw).strip()[:200] or f"Completado: {task.user_intent[:100]}"
        icon = "✅"
    else:
        message, icon = f"Completado: {task.user_intent[:100]}", "✅"
    return await log_activity(
        db=db, tenant_id=tenant_id, category="task",
        message=message, employee_id=employee_id, task_id=str(task.id), icon=icon,
    )


async def _broadcast(manager, tenant_id: str, payload: dict) -> None:
    try:
        await manager.broadcast_to_tenant(tenant_id, payload)
    except Exception as exc:
        logger.debug("WS broadcast error: %s", exc)


async def _execute_orchestrator(task_id: str):
    """Coordina: cargar tarea -> construir estado -> stream LangGraph -> persistir."""
    from app.agents.orchestrator import orchestrator
    from app.api.ws.notifications import manager

    async with AsyncSessionLocal() as db:
        # TODO Fase 3 (RLS): pasar tenant_id explícito al worker desde el dispatcher
        task = await _load_and_start_task(task_id, db)
        if not task:
            return

        employee_id: str | None = (task.additional_metadata or {}).get("addressed_employee_id")
        tenant_id = str(task.tenant_id)
        set_current_tenant(tenant_id)
        set_current_task(task_id)

        if employee_id:
            await _set_agent_status(db, employee_id, tenant_id, "working")
            await db.commit()
            await _broadcast(manager, tenant_id, {
                "type": "agent_status_changed", "employee_id": employee_id, "status": "working",
            })

        initial_state = await _build_initial_state(task, task_id, db)
        log_push(task_id, "Iniciando automatizacion...")

        try:
            final_state, usage_cb = await _stream_and_log(task_id, initial_state, orchestrator)
        except Exception:
            if employee_id:
                await _set_agent_status(db, employee_id, tenant_id, "idle")
                try:
                    await db.commit()
                except Exception:
                    pass
                await _broadcast(manager, tenant_id, {
                    "type": "agent_status_changed", "employee_id": employee_id, "status": "idle",
                })
            raise

        await _save_final_state(task, final_state, db)
        await _sync_workflow_artifacts(task, final_state, db)

        if employee_id and (usage_cb.total_tokens_in + usage_cb.total_tokens_out) > 0:
            from app.services.ai.employee_crud import record_token_usage
            await record_token_usage(
                employee_id=employee_id,
                tenant_id=tenant_id,
                task_id=task_id,
                tokens_in=usage_cb.total_tokens_in,
                tokens_out=usage_cb.total_tokens_out,
                cost_usd=usage_cb.total_cost_usd,
                provider=usage_cb._current_provider,
                db=db,
            )

        entry = await _log_task_completion(db, task, final_state, employee_id, tenant_id)
        if employee_id:
            await _set_agent_status(db, employee_id, tenant_id, "idle")
        await db.commit()

        if employee_id:
            await _broadcast(manager, tenant_id, {
                "type": "agent_status_changed", "employee_id": employee_id, "status": "idle",
            })
        if entry:
            await _broadcast(manager, tenant_id, {
                "type": "activity_new",
                "entry": {
                    "id": str(entry.id),
                    "employee_id": str(entry.employee_id) if entry.employee_id else None,
                    "category": entry.category,
                    "icon": entry.icon,
                    "message": entry.message,
                    "metadata": entry.metadata_json,
                    "created_at": entry.created_at.isoformat(),
                },
            })


async def _resume_orchestrator(task_id: str):
    """
    Reanuda la ejecucion despues de una aprobacion humana.
    Coordina: cargar tarea/approval -> crear factura -> re-invocar LangGraph.
    """
    from app.agents.orchestrator import OrchestratorState, TaskStatus, orchestrator

    async with AsyncSessionLocal() as db:
        # TODO Fase 3 (RLS): pasar tenant_id explícito al worker desde el dispatcher
        result = await _load_task_and_approval(task_id, db)
        if not result:
            return
        task, payload_data = result
        set_current_tenant(str(task.tenant_id))
        set_current_task(task_id)

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
