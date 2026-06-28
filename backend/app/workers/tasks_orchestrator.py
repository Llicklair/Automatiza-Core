"""
Tareas del orquestador LangGraph.
Coroutines puras ejecutadas por TaskRunner.
"""

import asyncio
import logging

from app.core.tenant_context import (
    get_current_tenant,
    set_current_task,
    set_current_tenant,
)
from app.db.base import AsyncSessionLocal
from app.services.exec_log_store import push as log_push
from app.services.idempotency import IdempotencyGuard
from app.workers._orchestrator_context import (
    _build_initial_state,
    _create_invoice_from_approval,
    _execute_from_approval,
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
    return isinstance(exc, ConnectionError | OSError | TimeoutError) or any(
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


async def execute_orchestrator(task_id: str, tenant_id: str | None = None):
    """Ejecuta el orquestador LangGraph para una tarea dada.

    Fase 3 (RLS): `tenant_id` se recibe del dispatcher cuando es conocido.
    Permite fijar el ContextVar antes de la SELECT de bootstrap de la Task.
    Si es None, se hace fallback al tenant_id de la fila (comportamiento previo).
    """
    guard = IdempotencyGuard()

    if await guard.already_executed("run_orchestrator", task_id):
        logger.info("[IDEMPOTENCY] run_orchestrator:%s ya ejecutado. Skip.", task_id)
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = await _execute_orchestrator(task_id, tenant_id)
        await guard.mark_executed("run_orchestrator", task_id, {"status": "done"})
        return result
    except Exception as exc:
        logger.exception("Error en run_orchestrator:%s", task_id)
        if _is_transient_error(exc):
            await guard.release("run_orchestrator", task_id)
            return await _retry(
                "run_orchestrator",
                task_id,
                lambda: _execute_orchestrator(task_id, tenant_id),
                guard,
                attempts=3,
                backoff_base=30,
            )
        await _mark_task_failed(task_id, str(exc))
        raise


async def resume_orchestrator(task_id: str, tenant_id: str | None = None):
    """Reanuda el orquestador tras una aprobacion humana.

    Fase 3 (RLS): ver execute_orchestrator para la semántica de tenant_id.
    """
    guard = IdempotencyGuard()

    if await guard.already_executed("resume_orchestrator", task_id):
        logger.info("[IDEMPOTENCY] resume_orchestrator:%s ya ejecutado. Skip.", task_id)
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = await _resume_orchestrator(task_id, tenant_id)
        await guard.mark_executed("resume_orchestrator", task_id, {"status": "done"})
        return result
    except Exception as exc:
        logger.exception("Error en resume_orchestrator:%s", task_id)
        # Espeja execute_orchestrator: SOLO los errores transitorios liberan la
        # idempotencia y reintentan. Un error NO transitorio (p.ej. tras crear la
        # factura) no debe reintentarse: `guard.release()` + retry re-ejecutaría
        # `_create_invoice_from_approval` y emitiría una factura DUPLICADA. Para
        # esos casos marcamos la tarea como fallida sin reintentar. (La creación de
        # factura es además idempotente por payload_key como defensa en profundidad.)
        if _is_transient_error(exc):
            await guard.release("resume_orchestrator", task_id)
            return await _retry(
                "resume_orchestrator",
                task_id,
                lambda: _resume_orchestrator(task_id, tenant_id),
                guard,
                attempts=3,
                backoff_base=10,
            )
        await _mark_task_failed(task_id, str(exc))
        raise


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
    is_clarification = bool((final_state.get("additional_metadata") or {}).get("clarification"))
    if error and is_clarification:
        # Petición de aclaración, no un fallo: se muestra tal cual, sin "Error:".
        message, icon = str(error)[:200], "🤔"
    elif error:
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


async def _record_run_usage(
    db,
    *,
    task,
    task_id: str,
    tenant_id: str,
    employee_id: str | None,
    usage_cb,
) -> None:
    """Persiste el consumo de tokens/coste de una ejecución del orquestador.

    Compartido por _execute_orchestrator y _resume_orchestrator para que tanto la
    ejecución normal como la reanudación-tras-aprobación registren la
    traza-resumen de coste (la que leen el modal de consumo de IA y el dashboard)
    y, si la task iba dirigida a un AIEmployee, su uso de tokens.
    """
    if (usage_cb.total_tokens_in + usage_cb.total_tokens_out) <= 0:
        return
    # Traza-resumen append-only con el coste real de la task. Sin esto las filas
    # de agent_execution_trace (insertadas por dispatch) no llevan tokens/cost y
    # el modal de consumo muestra 0 €.
    from app.services.observability import record_task_cost_trace
    await record_task_cost_trace(
        db,
        tenant_id=task.tenant_id,
        task_id=task.id,
        agent_name="orchestrator",
        tokens_in=usage_cb.total_tokens_in,
        tokens_out=usage_cb.total_tokens_out,
        cost_usd=usage_cb.total_cost_usd,
        llm_provider=usage_cb._current_provider,
    )
    if employee_id:
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


async def _execute_orchestrator(task_id: str, tenant_id_hint: str | None = None):
    """Coordina: cargar tarea -> construir estado -> stream LangGraph -> persistir.

    Fase 3 (RLS): si el dispatcher pasó `tenant_id_hint` lo fijamos en el
    ContextVar ANTES de la SELECT de bootstrap, de modo que RLS cubra la
    propia consulta de Task. La fila de DB sigue siendo la fuente de verdad
    y reafirma el contexto inmediatamente después (defensa en profundidad).
    """
    from app.agents.orchestrator import orchestrator
    from app.api.ws.notifications import manager

    # Fail-safe RLS: si no hay tenant por NINGÚN lado (hint None y ContextVar
    # vacío), abortamos antes de abrir la sesión. De lo contrario la SELECT de
    # bootstrap (_load_and_start_task) correría sin aislamiento; en prod RLS
    # fail-closed lo contiene, pero en dev/staging sin listener podría cargar
    # una Task de otro tenant. No afecta al path legítimo (hint válido, o hint
    # None con el ContextVar ya fijado por el caller).
    if not tenant_id_hint and not get_current_tenant():
        logger.error(
            "Orchestrator sin tenant (hint None y ContextVar vacío); aborto para "
            "no correr sin aislamiento. task=%s",
            task_id,
        )
        return

    if tenant_id_hint:
        set_current_tenant(tenant_id_hint)
        set_current_task(task_id)

    async with AsyncSessionLocal() as db:
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

        # El callback de uso lo posee el worker (no _stream_and_log) para poder
        # registrar el consumo aunque la tarea se cancele ("Detener") o falle.
        from app.core.llm_callbacks import UsageTrackingCallback

        usage_cb = UsageTrackingCallback(
            tenant_id=tenant_id,
            agent_name=initial_state.get("classified_domain") or "unknown",
        )

        try:
            final_state = await _stream_and_log(task_id, initial_state, orchestrator, usage_cb)
        except (Exception, asyncio.CancelledError):
            # Cancelación ("Detener") o error a mitad: registra el consumo PARCIAL
            # ya acumulado antes de propagar, para que el modal de consumo no salga
            # a 0 tras detener. Best-effort: nunca tapa la excepción original.
            try:
                await _record_run_usage(
                    db, task=task, task_id=task_id, tenant_id=tenant_id,
                    employee_id=employee_id, usage_cb=usage_cb,
                )
                await db.commit()
            except Exception:
                logger.warning(
                    "No se pudo registrar consumo parcial (task=%s)", task_id, exc_info=True
                )
            if employee_id:
                # La excepción original pudo dejar la sesión en transacción fallida;
                # sin rollback, el UPDATE de status + commit también fallarían y el
                # empleado quedaría colgado en "working".
                try:
                    await db.rollback()
                except Exception:
                    logger.debug(
                        "rollback previo a restaurar status falló (task=%s)",
                        task_id, exc_info=True,
                    )
                await _set_agent_status(db, employee_id, tenant_id, "idle")
                try:
                    await db.commit()
                except Exception as commit_err:
                    # Commit en cleanup de error: si falla, el AIEmployee queda con
                    # status="working" colgado y el siguiente health-check lo bloqueará.
                    # No volvemos a lanzar (la excepción original es la importante),
                    # pero sí logueamos para que el operador pueda detectar la fuga.
                    logger.warning(
                        "Commit fallido restaurando status='idle' del empleado %s "
                        "tras error en orchestrator (task=%s, tenant=%s): %s: %s",
                        employee_id, task_id, tenant_id,
                        type(commit_err).__name__, commit_err,
                    )
                await _broadcast(manager, tenant_id, {
                    "type": "agent_status_changed", "employee_id": employee_id, "status": "idle",
                })
            raise

        await _save_final_state(task, final_state, db)
        await _sync_workflow_artifacts(task, final_state, db)

        await _record_run_usage(
            db,
            task=task,
            task_id=task_id,
            tenant_id=tenant_id,
            employee_id=employee_id,
            usage_cb=usage_cb,
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


async def _resume_orchestrator(task_id: str, tenant_id_hint: str | None = None):
    """
    Reanuda la ejecucion despues de una aprobacion humana.
    Coordina: cargar tarea/approval -> crear factura -> re-invocar LangGraph.

    Fase 3 (RLS): ver _execute_orchestrator para la semántica de tenant_id_hint.
    """
    from app.agents.orchestrator import OrchestratorState, TaskStatus, orchestrator

    if tenant_id_hint:
        set_current_tenant(tenant_id_hint)
        set_current_task(task_id)

    async with AsyncSessionLocal() as db:
        result = await _load_task_and_approval(task_id, db)
        if not result:
            return
        task, payload_data = result
        set_current_tenant(str(task.tenant_id))
        set_current_task(task_id)

        # Acción estructurada ({kind, params}) → executor genérico. Payloads
        # antiguos sin kind → ruta legacy de factura.
        if payload_data.get("kind"):
            ok = await _execute_from_approval(task, payload_data, db)
        else:
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

        # Engancha el tracker de uso también en la reanudación: sin esto el LLM
        # que corre tras la aprobación no contabilizaba tokens (el modal de
        # consumo y el dashboard ignoraban el coste del tramo post-aprobación).
        from app.core.llm_callbacks import UsageTrackingCallback

        employee_id = (task.additional_metadata or {}).get("addressed_employee_id")
        usage_cb = UsageTrackingCallback(
            tenant_id=str(task.tenant_id), agent_name=task.domain or "unknown"
        )
        try:
            final_state = await orchestrator.ainvoke(
                initial_state, config={"recursion_limit": 50, "callbacks": [usage_cb]}
            )
        except (Exception, asyncio.CancelledError):
            # Cancelación/error en la reanudación: registra el consumo parcial.
            try:
                await _record_run_usage(
                    db, task=task, task_id=task_id, tenant_id=str(task.tenant_id),
                    employee_id=employee_id, usage_cb=usage_cb,
                )
                await db.commit()
            except Exception:
                logger.warning(
                    "No se pudo registrar consumo parcial en reanudación (task=%s)",
                    task_id, exc_info=True,
                )
            raise

        await _save_final_state(task, final_state, db)
        await _record_run_usage(
            db,
            task=task,
            task_id=task_id,
            tenant_id=str(task.tenant_id),
            employee_id=employee_id,
            usage_cb=usage_cb,
        )
        await db.commit()
