"""Instrumentación de la ejecución de agentes: resultados de error,
auditoría, broadcast de progreso por WebSocket y liberación de employees.

Las funciones reciben `state` como dict plano (solo leen tenant_id/task_id)
para no depender del TypedDict OrchestratorState de la capa de agentes.
"""

import asyncio
import logging
import uuid

from app.db.base import AsyncSessionLocal
from app.services.audit import log_action

logger = logging.getLogger(__name__)


def make_error_result(
    subtask: dict, agent_name: str, action: str, error: str, summary: str | None = None
) -> dict:
    return {
        "subtask_id": subtask["id"],
        "agent": agent_name,
        "success": False,
        "output": {"action": action, "error": error},
        "summary": summary or f"Error en {agent_name}: {error}",
        "error": error,
    }


async def release_employee(db, employee, *, label: str) -> None:
    """Marca el employee como idle y commitea, acotado a 10s.

    En timeout/error de graph.ainvoke la sesión puede quedar sucia (otros
    nodos del graph hicieron writes sin commit) y el commit posterior
    queda esperando locks. Sin acotar este cleanup, el TimeoutError de
    180s tardaba ~8min en propagarse al TaskRunner.
    """
    try:
        await db.rollback()
    except Exception:
        logger.debug("[ORCHESTRATOR] rollback de limpieza falló; continúo", exc_info=True)
    try:
        employee.status = "idle"
        await asyncio.wait_for(db.commit(), timeout=10)
    except Exception as commit_err:
        logger.warning(
            "[ORCHESTRATOR] cleanup post-%s para employee '%s' falló (status no actualizado): %s",
            label, getattr(employee, "name", "?"), commit_err,
        )


async def audit_log_result(
    state: dict,
    result: dict,
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


async def broadcast_progress(
    state: dict,
    result: dict,
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
