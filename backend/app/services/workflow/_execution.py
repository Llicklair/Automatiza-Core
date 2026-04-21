"""Funciones de ejecucion de workflows: run, dispatch, cancel, resume, steps."""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.agents.orchestrator import (
    _dispatch_banking,
    _dispatch_billing,
    _dispatch_compliance,
    _dispatch_crm,
    _dispatch_documents,
    _dispatch_email,
    _dispatch_excel,
    _dispatch_hr,
    _dispatch_rag,
)
from app.agents.tool_registry import call_tool
from app.db.models import models
from app.services.workflow.task_dispatch import (
    dispatch_node_engine,
    dispatch_orchestrator,
    dispatch_resume_node_engine,
)

logger = logging.getLogger(__name__)

_DISPATCH_MAP = {
    "billing": _dispatch_billing,
    "crm": _dispatch_crm,
    "documents": _dispatch_documents,
    "email": _dispatch_email,
    "excel": _dispatch_excel,
    "banking": _dispatch_banking,
    "hr": _dispatch_hr,
    "rag": _dispatch_rag,
    "compliance": _dispatch_compliance,
}


# ── Helpers internos ─────────────────────────────────────────────────────────


def _build_ai_instruction(workflow: models.Workflow) -> str:
    action_config = workflow.action_config or {}
    instruction = action_config.get("instruction") or action_config.get("intent")
    return instruction or workflow.description or workflow.name or "Ejecutar automatizacion"


def _infer_domain(workflow: models.Workflow) -> str:
    action_config = workflow.action_config or {}
    if action_config.get("agent") == "coordinator":
        return "coordinator"
    return "orchestrator"


# ── Dispatch helpers ─────────────────────────────────────────────────────────


async def _dispatch_deterministic(
    db,
    workflow,
    execution,
    tenant_id,
    user_id,
    intent_prefix: str,
    extra_meta: dict | None = None,
) -> None:
    """Crea Task determinista, ejecuta pasos y actualiza execution + task."""
    meta = {"workflow_id": str(workflow.id), "execution_id": str(execution.id)}
    if extra_meta:
        meta.update(extra_meta)
    task = models.Task(
        tenant_id=tenant_id,
        created_by=user_id,
        domain="deterministic",
        user_intent=f"{intent_prefix} {workflow.name}",
        status="running",
        additional_metadata=meta,
    )
    db.add(task)
    await db.flush()
    execution.task_id = task.id
    try:
        results = await execute_deterministic_steps(
            steps=workflow.compiled_steps,
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else "",
            task_id=str(task.id),
        )
        execution.status = "success"
        execution.result_log = f"{len(results)} paso(s). " + " | ".join(
            f"[{r.get('agent', '?')}] {'OK' if r.get('success') else 'ERR: ' + str(r.get('error', ''))[:60]}"
            for r in results
        )
        task.status = "done"
    except Exception as e:
        execution.status = "failed"
        execution.result_log = f"Error determinista: {e}"
        task.status = "failed"


async def _dispatch_reasoning(
    db,
    workflow,
    execution,
    tenant_id,
    user_id,
    intent: str,
    extra_meta: dict | None = None,
) -> models.Task:
    """Crea Task de reasoning, la vincula a execution y dispara el orquestador. Devuelve la Task."""
    meta = {"workflow_id": str(workflow.id), "execution_id": str(execution.id)}
    if extra_meta:
        meta.update(extra_meta)
    task = models.Task(
        tenant_id=tenant_id,
        created_by=user_id,
        domain=_infer_domain(workflow),
        user_intent=intent,
        status="pending",
        additional_metadata=meta,
    )
    db.add(task)
    await db.flush()
    execution.task_id = task.id
    await db.commit()
    try:
        await dispatch_orchestrator(str(task.id))
    except Exception as e:
        execution.status = "failed"
        execution.result_log = f"Error lanzando orchestrator: {e}"
    return task


# ── Run workflow ─────────────────────────────────────────────────────────────


async def run_workflow(
    workflow_id: UUID,
    tenant_id,
    user_id,
    db: AsyncSession,
) -> models.WorkflowExecution:
    """Ejecuta un workflow manualmente. Lanza ValueError si hay problemas."""
    from app.services.workflow.service import get_workflow

    workflow = await get_workflow(workflow_id, tenant_id, db)
    if not workflow:
        raise ValueError("Workflow no encontrado")
    if not workflow.is_active:
        raise ValueError("El workflow esta desactivado")

    existing = await db.execute(
        select(models.WorkflowExecution).where(
            models.WorkflowExecution.workflow_id == workflow_id,
            models.WorkflowExecution.status.in_(["running", "pending"]),
        )
    )
    if existing.scalars().first():
        raise ValueError(
            "Este workflow ya tiene una ejecucion en curso. Espera a que termine antes de lanzarlo de nuevo."
        )

    execution = models.WorkflowExecution(
        workflow_id=workflow.id,
        tenant_id=tenant_id,
        status="running",
        trigger_payload={"source": "manual_trigger", "user_id": str(user_id)},
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    from app.services.ai.node_engine import has_advanced_nodes

    if workflow.ui_nodes and has_advanced_nodes(workflow.ui_nodes, workflow.ui_edges):
        try:
            await dispatch_node_engine(str(execution.id))
            execution.result_log = (
                f"Motor de nodos lanzado para ejecucion [{str(execution.id)[:8]}...]."
            )
        except Exception as e:
            execution.result_log = f"Error al lanzar el motor de nodos: {e}"
            execution.status = "failed"

    elif workflow.execution_mode == "deterministic" and workflow.compiled_steps:
        await _dispatch_deterministic(db, workflow, execution, tenant_id, user_id, "[Determinista]")

    else:
        task = await _dispatch_reasoning(
            db, workflow, execution, tenant_id, user_id, _build_ai_instruction(workflow)
        )
        if execution.status != "failed":
            execution.result_log = f"Tarea IA lanzada [{str(task.id)[:8]}...]. El agente esta procesando la instruccion."

    await db.commit()
    await db.refresh(execution)
    return execution


async def run_workflow_with_context(
    workflow_id: UUID,
    context_msg: str,
    tenant_id,
    user_id,
    db: AsyncSession,
) -> models.WorkflowExecution:
    """Ejecuta un workflow con contexto adicional."""
    from app.services.workflow.service import get_workflow

    workflow = await get_workflow(workflow_id, tenant_id, db)
    if not workflow:
        raise ValueError("Workflow no encontrado")
    if not workflow.is_active:
        raise ValueError("El workflow esta desactivado")

    base_instruction = _build_ai_instruction(workflow)
    intent = (
        f"{base_instruction}\n\nContexto adicional: {context_msg}"
        if context_msg
        else base_instruction
    )

    execution = models.WorkflowExecution(
        workflow_id=workflow.id,
        tenant_id=tenant_id,
        status="running",
        trigger_payload={
            "source": "manual_with_context",
            "user_id": str(user_id),
            "context": context_msg,
        },
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    task = await _dispatch_reasoning(db, workflow, execution, tenant_id, user_id, intent)
    if execution.status != "failed":
        execution.result_log = f"Tarea IA lanzada con contexto [{str(task.id)[:8]}...]."

    await db.commit()
    await db.refresh(execution)
    return execution


# ── Cancel / Resume ──────────────────────────────────────────────────────────


async def cancel_execution(
    execution_id: UUID,
    workflow_id: UUID,
    tenant_id,
    db: AsyncSession,
) -> models.WorkflowExecution | None:
    from app.services.workflow.service import get_execution

    execution = await get_execution(execution_id, workflow_id, tenant_id, db)
    if not execution:
        return None
    if execution.status not in ("running", "paused"):
        raise ValueError(f"No se puede cancelar una ejecucion en estado '{execution.status}'")

    execution.status = "failed"
    execution.result_log = "Cancelado manualmente por el usuario."
    execution.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(execution)
    return execution


async def resume_execution(
    execution_id: UUID,
    workflow_id: UUID,
    tenant_id,
    db: AsyncSession,
) -> models.WorkflowExecution | None:
    from app.services.workflow.service import get_execution

    execution = await get_execution(execution_id, workflow_id, tenant_id, db)
    if not execution:
        return None
    if execution.status != "paused":
        raise ValueError(f"La ejecucion no esta pausada (estado: {execution.status})")
    if not execution.current_node_id:
        raise ValueError("No se puede determinar el nodo desde el que reanudar")

    await dispatch_resume_node_engine(str(execution_id), execution.current_node_id)
    execution.result_log = f"Reanudacion programada desde nodo {execution.current_node_id}."

    await db.commit()
    await db.refresh(execution)
    return execution


# ── Deterministic step execution ─────────────────────────────────────────────


def _run_deterministic_step(
    step: dict, idx: int, prev_output: str, tenant_id: str
) -> tuple[dict, str]:
    """Ejecuta un paso tool-directo. Devuelve (resultado, nuevo prev_output)."""
    agent_name = step.get("agent", "")
    tool_name = step.get("tool", "")
    if not tool_name:
        return (
            {
                "agent": agent_name,
                "step": idx,
                "type": "deterministic",
                "success": False,
                "error": "Paso sin campo 'tool'",
            },
            prev_output,
        )
    tool_params = {
        k: v.replace("$prev", prev_output) if isinstance(v, str) else v
        for k, v in step.get("params", {}).items()
    }
    tool_params.setdefault("tenant_id", tenant_id)
    try:
        output = call_tool(tool_name, tool_params)
        return (
            {
                "agent": agent_name,
                "step": idx,
                "type": "deterministic",
                "tool": tool_name,
                "success": True,
                "output": output,
                "error": None,
            },
            output,
        )
    except Exception as exc:
        return (
            {
                "agent": agent_name,
                "step": idx,
                "type": "deterministic",
                "tool": tool_name,
                "success": False,
                "error": str(exc),
            },
            prev_output,
        )


async def _run_reasoning_step(
    step: dict, idx: int, prev_output: str, base_state: dict
) -> tuple[dict, str]:
    """Ejecuta un paso LLM-reasoning. Devuelve (resultado, nuevo prev_output)."""
    agent_name = step.get("agent", "")
    intent = step.get("params", {}).get("intent", "").replace("$prev", prev_output)
    base_state["user_intent"] = intent
    base_state["current_intent"] = intent

    dispatch_fn = _DISPATCH_MAP.get(agent_name)
    if dispatch_fn is None:
        return (
            {
                "agent": agent_name,
                "step": idx,
                "type": "reasoning",
                "success": False,
                "error": f"Agente '{agent_name}' no reconocido",
            },
            prev_output,
        )
    subtask = {
        "id": f"hybrid_{idx}_{agent_name}",
        "subtask_id": f"hybrid_{idx}_{agent_name}",
        "agent": agent_name,
        "action": step.get("action", ""),
        "params": {"intent": intent},
        "depends_on": [],
        "status": "pending",
    }
    try:
        result = await dispatch_fn(base_state, subtask)
        output_data = result.get("output", {})
        new_prev = (
            output_data.get("response", "") if isinstance(output_data, dict) else str(output_data)
        )
        return (
            {
                "agent": agent_name,
                "step": idx,
                "type": "reasoning",
                "action": step.get("action", ""),
                "success": result.get("success", False),
                "output": output_data,
                "error": result.get("error"),
            },
            new_prev,
        )
    except Exception as exc:
        return (
            {
                "agent": agent_name,
                "step": idx,
                "type": "reasoning",
                "success": False,
                "error": str(exc),
            },
            prev_output,
        )


async def execute_deterministic_steps(
    steps: list[dict],
    tenant_id: str,
    user_id: str,
    task_id: str | None = None,
) -> list[dict]:
    """Ejecuta pasos precompilados de un workflow hibrido.

    Cada paso tiene 'type': "deterministic" (tool directo) o "reasoning" (LLM).
    """
    base_state: dict[str, Any] = {
        "task_id": task_id or str(uuid4()),
        "tenant_id": tenant_id,
        "user_id": user_id,
        "user_intent": "",
        "current_intent": None,
        "classified_domain": None,
        "plan": None,
        "current_step": 0,
        "agent_results": [],
        "requires_human_approval": False,
        "error_message": None,
    }

    results: list[dict] = []
    prev_output = ""

    for idx, step in enumerate(steps):
        step_type = step.get("type", "deterministic" if step.get("tool") else "reasoning")
        if step_type == "deterministic":
            result, prev_output = _run_deterministic_step(step, idx, prev_output, tenant_id)
        else:
            result, prev_output = await _run_reasoning_step(step, idx, prev_output, base_state)
        results.append(result)

    return results
