"""Node handlers: dispatch_node and all dispatch helpers."""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.agents.orchestrator.dispatchers import DISPATCHER_MAP, _dispatch_skill
from app.agents.orchestrator.state import (
    AgentResult,
    OrchestratorState,
    TaskStatus,
)
from app.db.base import AsyncSessionLocal
from app.db.models.ai_employees import AIEmployee
from app.services.audit import log_action
from app.services.execution_context import ExecutionContext

logger = logging.getLogger(__name__)

_TRANSIENT_ERRORS = (asyncio.TimeoutError, ConnectionError, OSError)


async def _invoke_dynamic_employee(
    enriched_state: dict,
    subtask: dict,
    agent_name: str,
    tenant_id: str,
) -> "AgentResult | None":
    """Busca un AIEmployee activo para el dominio y lo ejecuta vía compile_dynamic_agent.
    Devuelve None si no hay employee disponible."""
    from app.agents.workers import check_agent_budget, compile_dynamic_agent
    from app.services.workflow.activity import log_activity

    async with AsyncSessionLocal() as db:
        addressed_id = (enriched_state.get("additional_metadata") or {}).get("addressed_employee_id")
        if addressed_id and agent_name == "custom":
            try:
                emp_result = await db.execute(
                    select(AIEmployee).where(
                        AIEmployee.id == UUID(addressed_id),
                        AIEmployee.tenant_id == UUID(tenant_id),
                        AIEmployee.status.in_(["idle", "working", "pending_setup"]),
                    )
                )
                employee = emp_result.scalar_one_or_none()
            except Exception:
                employee = None
        else:
            emp_result = await db.execute(
                select(AIEmployee)
                .where(
                    AIEmployee.tenant_id == UUID(tenant_id),
                    AIEmployee.domain == agent_name,
                    AIEmployee.status.in_(["idle", "working"]),
                )
                .limit(1)
            )
            employee = emp_result.scalar_one_or_none()

        if not employee:
            return None

        has_budget = await check_agent_budget(str(employee.id), db)
        if not has_budget:
            return {
                "subtask_id": subtask["id"], "agent": agent_name, "success": False,
                "output": {"action": "budget_exceeded"},
                "error": f"Empleado IA '{employee.name}' pausado por presupuesto agotado.",
            }

        employee.status = "working"
        await db.commit()

        try:
            graph = await compile_dynamic_agent(str(employee.id), db)
            intent = (
                subtask.get("params", {}).get("intent")
                or enriched_state.get("current_intent")
                or enriched_state.get("user_intent", "")
            )
            result_state = await asyncio.wait_for(
                graph.ainvoke({
                    "tenant_id": tenant_id,
                    "task_id": enriched_state.get("task_id"),
                    "user_id": enriched_state.get("user_id"),
                    "user_intent": intent, "current_intent": intent,
                    "messages": [], "agent_results": [], "status": "running",
                }),
                timeout=120,
            )
            messages = result_state.get("messages", [])
            final_text = next(
                (msg.content for msg in reversed(messages)
                 if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip()),
                ""
            )
            success = not final_text.lower().startswith("error")
            try:
                await log_activity(db=db, tenant_id=tenant_id, employee_id=str(employee.id),
                                   category=agent_name, message=f"Ejecutó tarea: {final_text[:200]}")
            except Exception:
                pass
            employee.status = "idle"
            await db.commit()
            return {
                "subtask_id": subtask["id"], "agent": agent_name, "success": success,
                "output": {"action": "completed" if success else "failed", "response": final_text},
                "error": None if success else final_text,
            }
        except Exception as e:
            employee.status = "idle"
            await db.commit()
            logger.exception("Error en dynamic employee '%s'", employee.name)
            return {
                "subtask_id": subtask["id"], "agent": agent_name, "success": False,
                "output": {"action": "failed", "error": str(e)}, "error": str(e),
            }


async def _invoke_dispatcher(enriched_state: dict, subtask: dict, agent_name: str) -> AgentResult:
    """Routing: DISPATCHER_MAP → skill → AIEmployee dinámico → fallback."""
    dispatcher_fn = DISPATCHER_MAP.get(agent_name)
    if dispatcher_fn:
        return await asyncio.wait_for(dispatcher_fn(enriched_state, subtask), timeout=120)

    if agent_name == "skill" or (isinstance(agent_name, str) and agent_name.startswith("skill:")):
        return await _dispatch_skill(enriched_state, subtask)

    tenant_id = enriched_state.get("tenant_id")
    if tenant_id:
        try:
            result = await _invoke_dynamic_employee(enriched_state, subtask, agent_name, tenant_id)
            if result is not None:
                return result
        except Exception as e:
            logger.warning("Error en dynamic employee routing para '%s': %s", agent_name, e)

    return {
        "subtask_id": subtask["id"], "agent": agent_name, "success": True,
        "output": {"message": f"[PENDIENTE] Agente '{agent_name}' no implementado aún"},
        "error": None,
    }


async def _execute_one(
    idx: int, subtask: dict, state: dict, exec_ctx
) -> "tuple[int, dict, AgentResult]":
    """Ejecuta un paso individual con retry para errores transitorios."""
    agent_name = subtask["agent"]
    step_instruction = subtask.get("params", {}).get("intent")
    if exec_ctx:
        try:
            enriched = exec_ctx.build_enriched_intent(current_instruction=step_instruction)
        except Exception as _e:
            logger.warning("Error enriqueciendo intent con ExecutionContext: %s", _e)
            enriched = step_instruction or state.get("current_intent") or state["user_intent"]
    else:
        enriched = step_instruction or state.get("current_intent") or state["user_intent"]

    enriched_state = {**state, "current_intent": enriched}

    for attempt in range(2):
        try:
            result = await _invoke_dispatcher(enriched_state, subtask, agent_name)
            return idx, subtask, result
        except asyncio.TimeoutError:
            if attempt == 0:
                logger.warning("[ORCHESTRATOR] Timeout en agente '%s', reintentando (1/1)...", agent_name)
                await asyncio.sleep(2)
                continue
            result = {
                "subtask_id": subtask["id"], "agent": agent_name, "success": False,
                "output": {"action": "timeout", "error": f"El agente '{agent_name}' no respondió en 120s (2 intentos)"},
                "summary": f"Timeout: agente {agent_name} excedió 120s tras 2 intentos",
                "error": f"Timeout: el agente '{agent_name}' no respondió en 120s (2 intentos)",
            }
        except _TRANSIENT_ERRORS as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "rate" in err_str.lower() or "quota" in err_str.lower()
            if attempt == 0 and (isinstance(e, (ConnectionError, OSError)) or is_rate_limit):
                wait = 5 if is_rate_limit else 2
                logger.warning("[ORCHESTRATOR] Error transitorio en '%s': %s. Reintentando en %ds...",
                               agent_name, type(e).__name__, wait)
                await asyncio.sleep(wait)
                continue
            result = {
                "subtask_id": subtask["id"], "agent": agent_name, "success": False,
                "output": {"action": "failed", "error": f"{type(e).__name__}: {e}"},
                "summary": f"Error transitorio en agente {agent_name} tras retry: {e}",
                "error": str(e),
            }
        except Exception as e:
            logger.exception("Excepción no controlada en dispatcher '%s'", agent_name)
            result = {
                "subtask_id": subtask["id"], "agent": agent_name, "success": False,
                "output": {"action": "failed", "error": f"{type(e).__name__}: {e}"},
                "summary": f"Error inesperado en agente {agent_name}: {e}",
                "error": str(e),
            }
            break

    return idx, subtask, result


async def _audit_log_result(
    state: "OrchestratorState",
    result: "AgentResult",
    subtask: dict,
    agent_name: str,
    action_str: str,
) -> None:
    async with AsyncSessionLocal() as db:
        await log_action(
            db,
            tenant_id=uuid.UUID(state["tenant_id"]),
            task_id=uuid.UUID(state["task_id"]) if state.get("task_id") else None,
            agent_name=agent_name,
            action_type=action_str,
            status="success" if result["success"] else "failed",
            input_data={"subtask": subtask},
            output_data=result.get("output"),
            error_detail=result.get("error"),
        )
        await db.commit()


async def _broadcast_progress(
    state: "OrchestratorState",
    result: "AgentResult",
    agent_name: str,
    step_num: int,
    total_steps: int,
) -> None:
    try:
        from app.api.ws.notifications import manager as ws_manager

        await ws_manager.broadcast_to_tenant(
            state["tenant_id"],
            {
                "type": "task_progress",
                "task_id": state["task_id"],
                "step": step_num,
                "total_steps": total_steps,
                "agent": agent_name,
                "summary": result.get("summary", ""),
                "success": result["success"],
            },
        )
    except Exception as _ws_err:
        logger.debug("[WS] No se pudo emitir progreso: %s", _ws_err)


def _process_gathered_results(
    gathered: list,
    state: "OrchestratorState",
    plan: list,
    updated_plan: list,
    new_results: list,
    _audit_tasks: list,
) -> tuple[bool, str | None, bool, list]:
    """
    Procesa los resultados de los agentes ejecutados: actualiza plan, crea tareas
    de audit/broadcast y detecta aprobaciones y fallos críticos.

    Devuelve (has_critical_failure, critical_error, has_approval, approval_results).
    """
    has_critical_failure = False
    critical_error = None
    has_approval = False
    approval_results: list[AgentResult] = []

    for idx, subtask, result in gathered:
        agent_name = subtask["agent"]
        new_results.append(result)
        updated_plan[idx] = {**subtask, "status": "done" if result["success"] else "failed"}

        action_str = (
            result.get("output", {}).get("action", "unknown_action")
            if result.get("output")
            else "unknown_action"
        )

        _audit_tasks.append(asyncio.create_task(
            _audit_log_result(state, result, subtask, agent_name, action_str)
        ))

        _bc_task = asyncio.create_task(
            _broadcast_progress(state, result, agent_name, idx + 1, len(plan))
        )
        _bc_task.add_done_callback(
            lambda t: (
                logger.debug("[WS] Broadcast error: %s", t.exception())
                if not t.cancelled() and t.exception()
                else None
            )
        )

        if result.get("output", {}).get("action") == "approval_required":
            has_approval = True
            approval_results.append(result)

        if not result["success"]:
            _default_non_critical = {"excel", "documents"}
            is_non_critical = (
                subtask.get("critical") is False or agent_name in _default_non_critical
            )
            if is_non_critical:
                logger.warning(
                    "[ORCHESTRATOR] Agente no crítico '%s' falló, continuando.", agent_name
                )
                new_results.append(
                    {
                        "subtask_id": f"{subtask['id']}_warning",
                        "agent": "system",
                        "success": True,
                        "output": {
                            "action": "partial_failure_warning",
                            "response": f"Aviso: el paso '{agent_name}' no se completó ({result.get('error', 'error desconocido')}). El resto de la tarea se ejecutó correctamente.",
                        },
                        "summary": f"Fallo parcial en {agent_name}",
                        "error": None,
                    }
                )
            else:
                has_critical_failure = True
                critical_error = result.get("error")

    return has_critical_failure, critical_error, has_approval, approval_results


async def dispatch_node(state: OrchestratorState) -> OrchestratorState:
    """
    Invoca agentes especializados. Ejecuta en paralelo los pasos cuyas dependencias
    están resueltas. Usa ExecutionContext para enriquecer la intención con resultados previos.
    """
    # Guard: timeout global de tarea (máx 10 min)
    _MAX_TASK_SECONDS = 600
    _started_at = (state.get("additional_metadata") or {}).get("started_at")
    if _started_at:
        try:
            _elapsed = (datetime.now(UTC) - datetime.fromisoformat(_started_at)).total_seconds()
            if _elapsed > _MAX_TASK_SECONDS:
                logger.error("[ORCHESTRATOR] Tarea cancelada por timeout global: %.0fs > %ds", _elapsed, _MAX_TASK_SECONDS)
                return {
                    **state, "status": TaskStatus.FAILED,
                    "error_message": f"Tarea cancelada: superó el tiempo máximo de {_MAX_TASK_SECONDS}s (transcurridos {_elapsed:.0f}s)",
                }
        except Exception as _e:
            logger.warning("Error parseando started_at para timeout global: %s", _e)

    plan = state["plan"]
    updated_plan = list(plan)
    new_results = list(state["agent_results"])
    resolved_ids = {s["id"] for s in plan if s.get("status") in ("done", "failed")}
    failed_ids = {s["id"] for s in plan if s.get("status") == "failed"}

    ready: list[tuple[int, dict]] = []
    for idx, step in enumerate(plan):
        if step.get("status") != "pending":
            continue
        deps = step.get("depends_on", [])
        dep_failed = [d for d in deps if d in failed_ids]
        if dep_failed:
            logger.warning("[ORCHESTRATOR] Omitiendo paso '%s' (%s): dependencias fallidas %s",
                           step["id"], step["agent"], dep_failed)
            updated_plan[idx] = {**step, "status": "failed"}
            new_results.append({
                "subtask_id": step["id"], "agent": step["agent"], "success": False,
                "output": {"action": "skipped", "message": f"Paso omitido: dependencias fallidas ({', '.join(dep_failed)})"},
                "summary": "Paso omitido por dependencias fallidas",
                "error": f"Dependencias fallidas: {', '.join(dep_failed)}",
            })
            continue
        if all(d in resolved_ids for d in deps):
            ready.append((idx, step))

    if not ready:
        pending = [s for s in updated_plan if s.get("status") == "pending"]
        if pending:
            return {**state, "plan": updated_plan, "agent_results": new_results,
                    "status": TaskStatus.FAILED,
                    "error_message": "Deadlock: pasos pendientes con dependencias no resolubles",
                    "iteration_count": state["iteration_count"] + 1}
        return {**state, "plan": updated_plan, "agent_results": new_results,
                "status": TaskStatus.DONE, "iteration_count": state["iteration_count"] + 1}

    try:
        exec_ctx = ExecutionContext.from_state(state)
    except Exception as e:
        logger.warning("Error construyendo ExecutionContext: %s", e)
        exec_ctx = None

    if len(ready) == 1:
        gathered = [await _execute_one(*ready[0], state, exec_ctx)]
    else:
        logger.info("[ORCHESTRATOR] Ejecutando %d pasos en paralelo: %s",
                    len(ready), [s["id"] for _, s in ready])
        gathered = list(await asyncio.gather(*[_execute_one(idx, step, state, exec_ctx) for idx, step in ready]))

    # Procesar resultados, emitir audit/broadcast, y recopilar tareas de audit
    _audit_tasks: list[asyncio.Task] = []
    has_critical_failure, critical_error, has_approval, approval_results = (
        _process_gathered_results(gathered, state, plan, updated_plan, new_results, _audit_tasks)
    )

    # Esperar a que los audit logs se escriban (máx 5s) antes de devolver estado
    if _audit_tasks:
        done, pending = await asyncio.wait(_audit_tasks, timeout=5)
        for t in pending:
            logger.warning("[ORCHESTRATOR] Audit log no completó en 5s, dejando en background")
        for t in done:
            if t.exception():
                logger.error("Error en audit log: %s", t.exception())

    next_pending = next(
        (i for i, s in enumerate(updated_plan) if s.get("status") == "pending"), len(updated_plan)
    )

    if has_approval:
        first_approval = approval_results[0]
        if len(approval_results) > 1:
            logger.warning(
                "[ORCHESTRATOR] %d pasos requieren aprobación simultánea — pausando en la primera",
                len(approval_results),
            )
        return {
            **state,
            "plan": updated_plan,
            "agent_results": new_results,
            "current_step": next_pending,
            "status": TaskStatus.AWAITING_APPROVAL,
            "requires_human_approval": True,
            "approval_id": first_approval["output"].get("approval_id"),
            "iteration_count": state["iteration_count"] + 1,
        }

    if has_critical_failure:
        return {
            **state,
            "plan": updated_plan,
            "agent_results": new_results,
            "current_step": next_pending,
            "status": TaskStatus.FAILED,
            "error_message": critical_error,
            "iteration_count": state["iteration_count"] + 1,
        }

    new_status = TaskStatus.DONE if next_pending >= len(updated_plan) else TaskStatus.EXECUTING
    return {
        **state,
        "plan": updated_plan,
        "agent_results": new_results,
        "current_step": next_pending,
        "status": new_status,
        "iteration_count": state["iteration_count"] + 1,
    }
