"""
NodeEngine node-type execution handlers.

Extracted from node_engine.py to keep that file under 350 lines.
All functions receive the engine instance as first arg to access shared state.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import PendingApproval
from app.services.ai.condition_evaluator import _resolve_field, evaluate_condition
from app.services.ai.node_graph_helpers import (
    COMPLETED,
    FAILED,
    PAUSED,
    SKIPPED,
    WAITING,
    build_context_for_node,
    build_skill_dispatch,
    get_predecessors,
)
from app.services.audit import log_action
from app.services.workflow.task_dispatch import dispatch_resume_node_engine

if TYPE_CHECKING:
    from app.services.ai.node_engine import NodeEngine

_logger = logging.getLogger(__name__)


async def execute_skill_node(engine: NodeEngine, node: dict, db: AsyncSession) -> dict:
    """Ejecuta un nodo skill reutilizando las funciones _dispatch_* del orchestrator."""
    domain, instruction, subtask, mini_state = _build_skill_dispatch(engine, node)
    result = await _dispatch_agent(engine, domain, mini_state, subtask)

    try:
        action_str = (
            result.get("output", {}).get("action", "execute")
            if isinstance(result.get("output"), dict)
            else "execute"
        )
        await log_action(
            db,
            tenant_id=uuid.UUID(engine.tenant_id),
            agent_name=domain,
            action_type=action_str,
            status="success" if result.get("success") else "failed",
            input_data={"node_id": node["id"], "instruction": instruction},
            output_data=result.get("output"),
            error_detail=result.get("error"),
        )
        await db.flush()
    except Exception:
        _logger.warning(
            "Failed to audit skill node execution for node %s", node["id"], exc_info=True
        )

    return result.get("output", {})


async def run_agent_parallel(engine: NodeEngine, node: dict) -> dict:
    """
    Ejecuta un nodo skill sin sesión DB compartida (para asyncio.gather).
    Devuelve el dict node_state actualizado.
    """
    node_type = node.get("type", "skill")
    now = datetime.now(UTC).isoformat()

    if node_type not in ("skill", "action", "trigger"):
        return {
            "status": SKIPPED,
            "started_at": now,
            "output": {"reason": f"Node type '{node_type}' not parallelizable"},
            "completed_at": datetime.now(UTC).isoformat(),
        }
    if node_type == "trigger":
        return {
            "status": COMPLETED,
            "started_at": now,
            "output": engine.trigger_payload,
            "completed_at": datetime.now(UTC).isoformat(),
        }

    try:
        domain, _instruction, subtask, mini_state = _build_skill_dispatch(
            engine, node, extra_meta={"parallel": True}
        )
        result = await _dispatch_agent(engine, domain, mini_state, subtask)
        return {
            "status": COMPLETED if result.get("success", True) else FAILED,
            "started_at": now,
            "output": result.get("output", {}),
            "completed_at": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        return {
            "status": FAILED,
            "started_at": now,
            "output": {"error": str(e)},
            "completed_at": datetime.now(UTC).isoformat(),
        }


def execute_conditional_node(engine: NodeEngine, node: dict) -> str:
    """Evalúa la condición y devuelve 'true' o 'false'."""
    data = node.get("data", {})
    condition = data.get("condition", {})

    context = build_context_for_node(engine.edges, engine.node_states, node["id"])

    predecessors = get_predecessors(engine.edges, node["id"])
    if predecessors:
        last_pred = predecessors[-1]
        if last_pred in engine.node_states:
            context["prev"] = engine.node_states[last_pred]

    _logger.info(
        f"[CONDITIONAL] node={node['id']} condition={condition} context_keys={list(context.keys())}"
    )
    field = condition.get("field", "")
    resolved = _resolve_field(field, context)
    _logger.info(f"[CONDITIONAL] field='{field}' resolved_to={resolved}")

    result = evaluate_condition(condition, context)
    return "true" if result else "false"


async def execute_delay_node(engine: NodeEngine, node: dict, db: AsyncSession) -> dict:
    """Programa un resume tras delay_seconds."""
    data = node.get("data", {})
    delay_seconds = int(data.get("delay_seconds", 10))
    node_id = node["id"]

    engine.node_states[node_id]["status"] = WAITING
    engine.node_states[node_id]["output"] = {"delay_seconds": delay_seconds}

    execution = await engine._load_execution(db)
    if execution:
        execution.status = "running"
        execution.current_node_id = node_id
        execution.node_states = dict(engine.node_states)
        await db.flush()

    try:
        await dispatch_resume_node_engine(
            engine.execution_id,
            node_id,
            delay_seconds=delay_seconds,
        )
    except Exception as e:
        _logger.error("Error scheduling delay resume: %s", e)

    return {"suspend": True}


async def execute_approval_gate(engine: NodeEngine, node: dict, db: AsyncSession) -> dict:
    """Crea PendingApproval y pausa la ejecución."""
    data = node.get("data", {})
    description = (
        data.get("description") or data.get("label") or "Aprobación requerida para continuar"
    )
    node_id = node["id"]

    engine.node_states[node_id]["status"] = PAUSED
    engine.node_states[node_id]["output"] = {"description": description}

    approval = PendingApproval(
        task_id=uuid.uuid4(),
        tenant_id=uuid.UUID(engine.tenant_id),
        execution_id=uuid.UUID(engine.execution_id),
        action_description=description,
        action_payload={"node_id": node_id, "execution_id": engine.execution_id},
        risk_level="medium",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        status="pending",
    )
    db.add(approval)
    await db.flush()

    execution = await engine._load_execution(db)
    if execution:
        execution.status = "paused"
        execution.paused_at = datetime.now(UTC)
        execution.current_node_id = node_id
        execution.node_states = dict(engine.node_states)
        await db.flush()

    return {"suspend": True}


# ── private helpers ───────────────────────────────────────────────────────────


def _build_skill_dispatch(
    engine: NodeEngine, node: dict, extra_meta: dict | None = None
) -> tuple[str, str, dict, dict]:
    return build_skill_dispatch(
        node,
        engine.edges,
        engine.node_states,
        engine.tenant_id,
        engine.user_id,
        engine.execution_id,
        extra_meta,
    )


async def _dispatch_agent(engine: NodeEngine, domain: str, state: dict, subtask: dict) -> dict:
    from app.services.ai.node_dispatch import dispatch_agent

    return await dispatch_agent(domain, state, subtask)
