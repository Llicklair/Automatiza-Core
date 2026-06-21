"""
Sub-módulo del orquestador: funciones que actualizan estado en BD
(Task, Workflow, WorkflowExecution, TenantDocument).
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import (
    Task,
    TenantDocument,
)
from app.db.models.models import (
    Workflow as WFModel,
)
from app.db.models.models import (
    WorkflowExecution as WFExec,
)

logger = logging.getLogger(__name__)


async def _mark_task_failed(task_id: str, error_msg: str):
    """Marca una tarea como fallida en BD directamente (sin pasar por el orquestador)."""
    try:
        task_uuid = uuid.UUID(task_id) if isinstance(task_id, str) else task_id
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Task).where(Task.id == task_uuid))
            task = result.scalar_one_or_none()
            if task:
                task.status = "failed"
                task.error_message = f"Error interno del agente: {error_msg[:500]}"
                task.completed_at = datetime.now(UTC)
                await db.commit()
    except Exception:
        logger.debug("No se pudo marcar tarea %s como fallida en BD", task_id, exc_info=True)


def _plan_to_ui_graph(plan: list, trigger_type: str) -> tuple[list, list]:
    """Delegated to services/workflow — kept as thin wrapper for internal use."""
    from app.services.workflow import plan_to_ui_graph

    return plan_to_ui_graph(plan, trigger_type)


async def _save_final_state(task, final_state: dict, db) -> None:
    """Persist LangGraph final state into the Task row. Shared by execute & resume."""
    status_val = final_state.get("status")
    task.status = (
        status_val.value if hasattr(status_val, "value") else (status_val or "failed")
    )
    task.plan = final_state.get("plan")
    task.agent_results = final_state.get("agent_results", [])
    task.current_step = final_state.get("current_step", 0)
    task.requires_human_approval = final_state.get("requires_human_approval", False)
    task.error_message = final_state.get("error_message")
    if "additional_metadata" in final_state:
        task.additional_metadata = final_state["additional_metadata"]

    if task.status in ("done", "failed"):
        task.completed_at = datetime.now(UTC)


async def _update_workflow_topology(task, plan_list: list, db) -> None:
    """Guarda la topologia visual (ui_nodes/ui_edges) en el Workflow si aun no tiene."""
    wf_id = (task.additional_metadata or {}).get("workflow_id")
    if not wf_id or not plan_list:
        return
    wf_res = await db.execute(select(WFModel).where(WFModel.id == uuid.UUID(wf_id)))
    wf_record = wf_res.scalar_one_or_none()
    if wf_record and not wf_record.ui_nodes:
        wf_record.ui_nodes, wf_record.ui_edges = _plan_to_ui_graph(
            plan_list, wf_record.trigger_type or "manual"
        )


async def _update_workflow_execution(task, db) -> None:
    """Sincroniza el estado del WorkflowExecution vinculado con el estado de la tarea."""
    wf_exec_id = (task.additional_metadata or {}).get("execution_id")
    if not wf_exec_id:
        return
    exec_res = await db.execute(select(WFExec).where(WFExec.id == uuid.UUID(wf_exec_id)))
    wf_exec = exec_res.scalar_one_or_none()
    # Acepta también `pending`: el event_bus crea executions con `pending`
    # (no `running`), por lo que sin esto el sync no actualizaba nunca y
    # las executions event-driven quedaban en pending eternamente aunque
    # la task completara done/failed.
    if not wf_exec or wf_exec.status not in ("running", "pending"):
        return

    wf_exec.status = {"done": "success", "failed": "failed", "awaiting_approval": "paused"}.get(
        task.status, "running"
    )
    if task.status in ("done", "failed"):
        wf_exec.completed_at = datetime.now(UTC)
    wf_exec.result_log = (
        task.error_message
        or (str(task.agent_results[-1].get("output", "")) if task.agent_results else None)
        or wf_exec.result_log
    )


async def _update_linked_document(task, final_state: dict, db) -> None:
    """Actualiza el TenantDocument vinculado a la tarea con el resultado del agente."""
    doc_res = await db.execute(select(TenantDocument).where(TenantDocument.task_id == task.id))
    linked_doc = doc_res.scalars().first()
    if not linked_doc:
        return

    if task.status != "done":
        linked_doc.status = "failed"
        return

    linked_doc.status = "processed"
    linked_doc.processed_at = datetime.now(UTC)
    results = final_state.get("agent_results", [])
    if results:
        output = results[-1].get("output", {})
        if isinstance(output, dict):
            classified = output.get("classified") or {}
            summary = (
                classified.get("summary")
                or output.get("summary")
                or output.get("respuesta_consulta")
                or output.get("alertas_redactadas", [""])[0]
            )
            linked_doc.parsed_content = summary or str(output)
        else:
            linked_doc.parsed_content = str(output)


async def _sync_workflow_artifacts(task, final_state: dict, db) -> None:
    """Sincroniza topologia, ejecucion y documento vinculados tras finalizar la tarea."""
    await _update_workflow_topology(task, final_state.get("plan"), db)
    await _update_workflow_execution(task, db)
    await _update_linked_document(task, final_state, db)
