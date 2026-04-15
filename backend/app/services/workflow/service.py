"""Servicio de dominio para Workflows & Automatizaciones.

Encapsula: CRUD de workflows, ejecución manual/con contexto/por evento,
parsing NL, ejecución determinista, y generación de preview nodes.
"""

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from langchain_core.messages import HumanMessage, SystemMessage
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
from app.core.llm_factory import get_llm
from app.db.models import models
from app.prompts import load_prompt
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


# ── CRUD ─────────────────────────────────────────────────────────────────────


async def list_workflows(tenant_id, db: AsyncSession) -> list[models.Workflow]:
    result = await db.execute(
        select(models.Workflow).where(models.Workflow.tenant_id == tenant_id)
    )
    return list(result.scalars().all())


async def create_workflow(workflow_in, tenant_id, user_id, db: AsyncSession) -> models.Workflow:
    db_workflow = models.Workflow(
        tenant_id=tenant_id,
        created_by=user_id,
        name=workflow_in.name,
        description=workflow_in.description,
        is_active=workflow_in.is_active,
        trigger_type=workflow_in.trigger_type,
        trigger_config=workflow_in.trigger_config,
        action_type=workflow_in.action_type,
        action_config=workflow_in.action_config,
        execution_mode=workflow_in.execution_mode,
        compiled_steps=workflow_in.compiled_steps if hasattr(workflow_in, "compiled_steps") else None,
        ui_nodes=workflow_in.ui_nodes or [],
        ui_edges=workflow_in.ui_edges or [],
    )
    db.add(db_workflow)
    await db.commit()
    await db.refresh(db_workflow)
    return db_workflow


async def get_workflow(workflow_id: UUID, tenant_id, db: AsyncSession) -> models.Workflow | None:
    result = await db.execute(
        select(models.Workflow).where(
            models.Workflow.id == workflow_id, models.Workflow.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


async def update_workflow(
    workflow_id: UUID, workflow_in, tenant_id, db: AsyncSession,
) -> models.Workflow | None:
    wf = await get_workflow(workflow_id, tenant_id, db)
    if not wf:
        return None
    update_data = workflow_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(wf, key, value)
    await db.commit()
    await db.refresh(wf)
    return wf


async def delete_workflow(workflow_id: UUID, tenant_id, db: AsyncSession) -> bool:
    wf = await get_workflow(workflow_id, tenant_id, db)
    if not wf:
        return False
    await db.delete(wf)
    await db.commit()
    return True


# ── Recent completions ───────────────────────────────────────────────────────


async def recent_completions(tenant_id, since: float, db: AsyncSession) -> list[dict]:
    since_dt = (
        datetime.fromtimestamp(since, tz=UTC) if since > 0 else datetime.now(UTC)
    )
    stmt = (
        select(
            models.WorkflowExecution.id,
            models.WorkflowExecution.status,
            models.WorkflowExecution.completed_at,
            models.Workflow.name,
        )
        .join(models.Workflow, models.WorkflowExecution.workflow_id == models.Workflow.id)
        .where(
            models.WorkflowExecution.tenant_id == tenant_id,
            models.WorkflowExecution.status.in_(["completed", "success", "failed"]),
            models.WorkflowExecution.completed_at >= since_dt,
        )
        .order_by(models.WorkflowExecution.completed_at.desc())
        .limit(5)
    )
    result = await db.execute(stmt)
    rows = result.fetchall()
    return [
        {
            "id": str(r[0]),
            "status": r[1],
            "completed_at": r[2].isoformat() if r[2] else None,
            "workflow_name": r[3],
        }
        for r in rows
    ]


# ── Execution helpers ────────────────────────────────────────────────────────


async def get_execution(
    execution_id: UUID, workflow_id: UUID, tenant_id, db: AsyncSession,
) -> models.WorkflowExecution | None:
    result = await db.execute(
        select(models.WorkflowExecution).where(
            models.WorkflowExecution.id == execution_id,
            models.WorkflowExecution.workflow_id == workflow_id,
            models.WorkflowExecution.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def list_executions(
    workflow_id: UUID, tenant_id, db: AsyncSession,
) -> list[models.WorkflowExecution]:
    result = await db.execute(
        select(models.WorkflowExecution)
        .where(
            models.WorkflowExecution.workflow_id == workflow_id,
            models.WorkflowExecution.tenant_id == tenant_id,
        )
        .order_by(models.WorkflowExecution.started_at.desc())
        .limit(20)
    )
    return list(result.scalars().all())


async def get_execution_logs(
    execution_id: UUID, workflow_id: UUID, tenant_id, db: AsyncSession,
) -> dict:
    execution = await get_execution(execution_id, workflow_id, tenant_id, db)
    if not execution:
        return None

    lines: list[str] = []
    if execution.task_id:
        try:
            from app.services.exec_log_store import get_all
            stored_lines = get_all(str(execution.task_id))
            if stored_lines:
                lines = stored_lines
        except Exception:
            logger.debug("exec_log_store unavailable, using result_log fallback", exc_info=True)

    if not lines and execution.result_log:
        lines = [execution.result_log]

    return {"lines": lines, "status": execution.status}


# ── Execution dispatch helpers ────────────────────────────────────────────────


async def _dispatch_deterministic(
    db, workflow, execution, tenant_id, user_id, intent_prefix: str, extra_meta: dict | None = None,
) -> None:
    """Crea Task determinista, ejecuta pasos y actualiza execution + task."""
    meta = {"workflow_id": str(workflow.id), "execution_id": str(execution.id)}
    if extra_meta:
        meta.update(extra_meta)
    task = models.Task(
        tenant_id=tenant_id, created_by=user_id, domain="deterministic",
        user_intent=f"{intent_prefix} {workflow.name}", status="running",
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
        execution.result_log = (
            f"{len(results)} paso(s). "
            + " | ".join(
                f"[{r.get('agent', '?')}] {'OK' if r.get('success') else 'ERR: ' + str(r.get('error', ''))[:60]}"
                for r in results
            )
        )
        task.status = "done"
    except Exception as e:
        execution.status = "failed"
        execution.result_log = f"Error determinista: {e}"
        task.status = "failed"


async def _dispatch_reasoning(
    db, workflow, execution, tenant_id, user_id, intent: str, extra_meta: dict | None = None,
) -> models.Task:
    """Crea Task de reasoning, la vincula a execution y dispara el orquestador. Devuelve la Task."""
    meta = {"workflow_id": str(workflow.id), "execution_id": str(execution.id)}
    if extra_meta:
        meta.update(extra_meta)
    task = models.Task(
        tenant_id=tenant_id, created_by=user_id, domain=_infer_domain(workflow),
        user_intent=intent, status="pending", additional_metadata=meta,
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
    workflow_id: UUID, tenant_id, user_id, db: AsyncSession,
) -> models.WorkflowExecution:
    """Ejecuta un workflow manualmente. Lanza ValueError si hay problemas."""
    workflow = await get_workflow(workflow_id, tenant_id, db)
    if not workflow:
        raise ValueError("Workflow no encontrado")
    if not workflow.is_active:
        raise ValueError("El workflow está desactivado")

    existing = await db.execute(
        select(models.WorkflowExecution).where(
            models.WorkflowExecution.workflow_id == workflow_id,
            models.WorkflowExecution.status.in_(["running", "pending"]),
        )
    )
    if existing.scalars().first():
        raise ValueError(
            "Este workflow ya tiene una ejecución en curso. Espera a que termine antes de lanzarlo de nuevo."
        )

    execution = models.WorkflowExecution(
        workflow_id=workflow.id, tenant_id=tenant_id, status="running",
        trigger_payload={"source": "manual_trigger", "user_id": str(user_id)},
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    from app.services.ai.node_engine import has_advanced_nodes

    if workflow.ui_nodes and has_advanced_nodes(workflow.ui_nodes, workflow.ui_edges):
        try:
            await dispatch_node_engine(str(execution.id))
            execution.result_log = f"Motor de nodos lanzado para ejecución [{str(execution.id)[:8]}...]."
        except Exception as e:
            execution.result_log = f"Error al lanzar el motor de nodos: {e}"
            execution.status = "failed"

    elif workflow.execution_mode == "deterministic" and workflow.compiled_steps:
        await _dispatch_deterministic(db, workflow, execution, tenant_id, user_id, "[Determinista]")

    else:
        task = await _dispatch_reasoning(db, workflow, execution, tenant_id, user_id, _build_ai_instruction(workflow))
        if execution.status != "failed":
            execution.result_log = f"Tarea IA lanzada [{str(task.id)[:8]}...]. El agente esta procesando la instruccion."

    await db.commit()
    await db.refresh(execution)
    return execution


async def run_workflow_with_context(
    workflow_id: UUID, context_msg: str, tenant_id, user_id, db: AsyncSession,
) -> models.WorkflowExecution:
    """Ejecuta un workflow con contexto adicional."""
    workflow = await get_workflow(workflow_id, tenant_id, db)
    if not workflow:
        raise ValueError("Workflow no encontrado")
    if not workflow.is_active:
        raise ValueError("El workflow está desactivado")

    base_instruction = _build_ai_instruction(workflow)
    intent = f"{base_instruction}\n\nContexto adicional: {context_msg}" if context_msg else base_instruction

    execution = models.WorkflowExecution(
        workflow_id=workflow.id, tenant_id=tenant_id, status="running",
        trigger_payload={"source": "manual_with_context", "user_id": str(user_id), "context": context_msg},
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
    execution_id: UUID, workflow_id: UUID, tenant_id, db: AsyncSession,
) -> models.WorkflowExecution | None:
    execution = await get_execution(execution_id, workflow_id, tenant_id, db)
    if not execution:
        return None
    if execution.status not in ("running", "paused"):
        raise ValueError(f"No se puede cancelar una ejecución en estado '{execution.status}'")

    execution.status = "failed"
    execution.result_log = "Cancelado manualmente por el usuario."
    execution.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(execution)
    return execution


async def resume_execution(
    execution_id: UUID, workflow_id: UUID, tenant_id, db: AsyncSession,
) -> models.WorkflowExecution | None:
    execution = await get_execution(execution_id, workflow_id, tenant_id, db)
    if not execution:
        return None
    if execution.status != "paused":
        raise ValueError(f"La ejecución no está pausada (estado: {execution.status})")
    if not execution.current_node_id:
        raise ValueError("No se puede determinar el nodo desde el que reanudar")

    await dispatch_resume_node_engine(str(execution_id), execution.current_node_id)
    execution.result_log = f"Reanudación programada desde nodo {execution.current_node_id}."

    await db.commit()
    await db.refresh(execution)
    return execution


# ── Parse NL ─────────────────────────────────────────────────────────────────


async def parse_natural_language(text: str) -> dict:
    """Convierte prompt de lenguaje natural en configuración de workflow.

    Raises Exception si el LLM no puede parsear.
    """
    llm = get_llm(temperature=0, format_output="json")
    llm_plain = get_llm(temperature=0)

    sys_prompt = load_prompt("workflow_parse")
    response = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=text)])
    raw = response.content.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.endswith("```"):
        raw = raw[:-3]
    payload = json.loads(raw.strip())

    # Detección de determinismo
    can_det = False
    try:
        instruction = payload.get("action_config", {}).get("instruction", text)
        det_prompt = load_prompt("workflow_determinism_check")
        det_response = llm_plain.invoke([
            SystemMessage(content=det_prompt),
            HumanMessage(content=instruction),
        ])
        can_det = det_response.content.strip().lower().startswith("true")
    except Exception as det_err:
        logger.warning("Fallo detección determinismo: %s", det_err)
    payload["can_be_deterministic"] = can_det

    preview_nodes, preview_edges = generate_preview_nodes(payload)
    payload["ui_nodes"] = preview_nodes
    payload["ui_edges"] = preview_edges
    return payload


# ── Fire event ───────────────────────────────────────────────────────────────


async def fire_event(
    event_name: str, context: dict, tenant_id, user_id, db: AsyncSession,
) -> list[str]:
    """Dispara todos los workflows activos que coincidan con el evento. Retorna IDs disparados."""
    result = await db.execute(
        select(models.Workflow).where(
            models.Workflow.tenant_id == tenant_id,
            models.Workflow.is_active.is_(True),
            models.Workflow.trigger_type == "event_based",
        )
    )
    workflows = result.scalars().all()

    triggered = []
    for wf in workflows:
        wf_events = wf.trigger_config.get("events", [])
        if event_name not in wf_events and "any" not in wf_events:
            continue

        execution = models.WorkflowExecution(
            workflow_id=wf.id,
            tenant_id=tenant_id,
            status="running",
            trigger_payload={"event": event_name, "context": context},
        )
        db.add(execution)
        await db.flush()

        extra_meta = {"event": event_name}
        if wf.execution_mode == "deterministic" and wf.compiled_steps:
            await _dispatch_deterministic(
                db, wf, execution, tenant_id, user_id,
                f"[Determinista] ({event_name})", extra_meta,
            )
            if execution.status == "success":
                triggered.append(str(wf.id))
            await db.commit()
        else:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            intent = f"{_build_ai_instruction(wf)} [Contexto: {event_name} - {context_str}]"
            await _dispatch_reasoning(db, wf, execution, tenant_id, user_id, intent, extra_meta)
            if execution.status != "failed":
                triggered.append(str(wf.id))
            await db.commit()

    return triggered


# ── Deterministic execution ──────────────────────────────────────────────────


def _run_deterministic_step(step: dict, idx: int, prev_output: str, tenant_id: str) -> tuple[dict, str]:
    """Ejecuta un paso tool-directo. Devuelve (resultado, nuevo prev_output)."""
    agent_name = step.get("agent", "")
    tool_name = step.get("tool", "")
    if not tool_name:
        return (
            {"agent": agent_name, "step": idx, "type": "deterministic",
             "success": False, "error": "Paso sin campo 'tool'"},
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
            {"agent": agent_name, "step": idx, "type": "deterministic",
             "tool": tool_name, "success": True, "output": output, "error": None},
            output,
        )
    except Exception as exc:
        return (
            {"agent": agent_name, "step": idx, "type": "deterministic",
             "tool": tool_name, "success": False, "error": str(exc)},
            prev_output,
        )


async def _run_reasoning_step(step: dict, idx: int, prev_output: str, base_state: dict) -> tuple[dict, str]:
    """Ejecuta un paso LLM-reasoning. Devuelve (resultado, nuevo prev_output)."""
    agent_name = step.get("agent", "")
    intent = step.get("params", {}).get("intent", "").replace("$prev", prev_output)
    base_state["user_intent"] = intent
    base_state["current_intent"] = intent

    dispatch_fn = _DISPATCH_MAP.get(agent_name)
    if dispatch_fn is None:
        return (
            {"agent": agent_name, "step": idx, "type": "reasoning",
             "success": False, "error": f"Agente '{agent_name}' no reconocido"},
            prev_output,
        )
    subtask = {
        "id": f"hybrid_{idx}_{agent_name}", "subtask_id": f"hybrid_{idx}_{agent_name}",
        "agent": agent_name, "action": step.get("action", ""),
        "params": {"intent": intent}, "depends_on": [], "status": "pending",
    }
    try:
        result = await dispatch_fn(base_state, subtask)
        output_data = result.get("output", {})
        new_prev = output_data.get("response", "") if isinstance(output_data, dict) else str(output_data)
        return (
            {"agent": agent_name, "step": idx, "type": "reasoning",
             "action": step.get("action", ""), "success": result.get("success", False),
             "output": output_data, "error": result.get("error")},
            new_prev,
        )
    except Exception as exc:
        return (
            {"agent": agent_name, "step": idx, "type": "reasoning",
             "success": False, "error": str(exc)},
            prev_output,
        )


async def execute_deterministic_steps(
    steps: list[dict],
    tenant_id: str,
    user_id: str,
    task_id: str | None = None,
) -> list[dict]:
    """Ejecuta pasos precompilados de un workflow híbrido.

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


# ── Plan / Preview node generation ───────────────────────────────────────────

_AGENT_TYPES = {
    "billing": "skill",
    "hr": "skill",
    "crm": "skill",
    "advisory": "skill",
    "banking": "skill",
    "documents": "skill",
    "compliance": "skill",
    "rag": "skill",
    "excel": "skill",
    "email": "skill",
    "coordinator": "action",
    "workflow": "action",
    "orchestrator": "action",
    "skill": "skill",
}

_AGENT_LABELS = {
    "billing": "Facturacion",
    "hr": "RRHH",
    "crm": "CRM",
    "advisory": "Asesoria Fiscal",
    "banking": "Banca",
    "documents": "Documentos",
    "compliance": "Cumplimiento",
    "rag": "Busqueda RAG",
    "excel": "Excel",
    "email": "Email",
    "coordinator": "Coordinador",
    "orchestrator": "Orquestador",
    "workflow": "Workflow",
}

_TRIGGER_LABELS = {
    "event_based": "Evento ERP",
    "schedule_based": "Programación",
    "manual": "Inicio Manual",
}


def plan_to_ui_graph(plan: list, trigger_type: str) -> tuple[list, list]:
    """Convierte el plan del orquestador (lista de SubTask) en nodos y aristas ReactFlow."""
    nodes: list[dict] = []
    edges: list[dict] = []

    # Nodo trigger
    nodes.append({
        "id": "trigger",
        "type": "trigger",
        "position": {"x": 250, "y": 0},
        "data": {
            "label": _TRIGGER_LABELS.get(trigger_type, "Trigger"),
            "trigger_type": trigger_type,
        },
    })

    # Indice id -> posicion
    step_id_to_index: dict[str, int] = {}
    for i, step in enumerate(plan):
        step_id_to_index[step.get("id", f"step_{i}")] = i

    # Capas topologicas
    layers: dict[str, int] = {}
    for i, step in enumerate(plan):
        step_id = step.get("id", f"step_{i}")
        deps = step.get("depends_on", [])
        if not deps:
            layers[step_id] = 0
        else:
            layers[step_id] = max(layers.get(d, 0) for d in deps) + 1

    # Agrupar por capa y posicionar
    layer_groups: dict[int, list] = defaultdict(list)
    for i, step in enumerate(plan):
        step_id = step.get("id", f"step_{i}")
        layer_groups[layers.get(step_id, i)].append((i, step_id, step))

    COL_W, ROW_H = 220, 130
    for layer_idx in sorted(layer_groups.keys()):
        items = layer_groups[layer_idx]
        total_w = len(items) * COL_W
        start_x = 250 - total_w // 2 + COL_W // 2
        for col_idx, (_original_idx, step_id, step) in enumerate(items):
            agent = step.get("agent", step.get("domain", "skill"))
            nodes.append({
                "id": step_id,
                "type": _AGENT_TYPES.get(agent, "skill"),
                "position": {"x": start_x + col_idx * COL_W, "y": 150 + layer_idx * ROW_H},
                "data": {
                    "label": _AGENT_LABELS.get(agent, agent.title()),
                    "domain": agent,
                    "description": step.get("action", step.get("instruction", ""))[:120],
                },
            })
            deps = step.get("depends_on", [])
            if deps:
                for dep_id in deps:
                    edges.append({"id": f"e-{dep_id}-{step_id}", "source": dep_id, "target": step_id})
            else:
                edges.append({"id": f"e-trigger-{step_id}", "source": "trigger", "target": step_id})

    return nodes, edges

_INSTRUCTION_TO_AGENT = [
    (["factura", "cobro", "pago", "billing", "invoice"], "billing", "Facturación"),
    (["empleado", "nómina", "nomina", "rrhh", "salario", "hr"], "hr", "RRHH"),
    (["cliente", "crm", "venta", "oportunidad", "contacto"], "crm", "CRM"),
    (["fiscal", "impuesto", "iva", "irpf", "aeat", "advisory"], "advisory", "Asesoría Fiscal"),
    (["banco", "cuenta", "transferencia", "banking"], "banking", "Banca"),
    (["documento", "archivo", "ocr", "contrato", "pdf"], "documents", "Documentos"),
    (["email", "correo", "envía", "envia", "notifica"], "email", "Email"),
    (["excel", "hoja", "informe", "reporte"], "excel", "Excel / Informe"),
]


def generate_preview_nodes(payload: dict) -> tuple[list, list]:
    """Genera topología visual mínima a partir del payload parseado por IA."""
    trigger_type = payload.get("trigger_type", "manual")
    instruction = (payload.get("action_config") or {}).get("instruction", "")
    description = payload.get("description", "")
    text = (instruction + " " + description).lower()

    detected = []
    for keywords, agent, label in _INSTRUCTION_TO_AGENT:
        if any(kw in text for kw in keywords):
            detected.append((agent, label))
    if not detected:
        detected = [("skill", "Agente IA")]

    CENTER_X = 300
    nodes = [{
        "id": "trigger", "type": "trigger",
        "position": {"x": CENTER_X, "y": 0},
        "data": {"label": _TRIGGER_LABELS.get(trigger_type, "Trigger"), "trigger_type": trigger_type},
    }]
    edges = []

    if len(detected) <= 1:
        agent, label = detected[0]
        node_id = "preview_agent_0"
        nodes.append({
            "id": node_id, "type": "skill",
            "position": {"x": CENTER_X, "y": 160},
            "data": {"label": label, "domain": agent, "instruction": instruction[:200]},
        })
        edges.append({"id": f"e-trigger-{node_id}", "source": "trigger", "target": node_id})
    else:
        SPACING = 280
        total_width = (len(detected) - 1) * SPACING
        start_x = CENTER_X - total_width / 2
        branch_ids = []

        for i, (agent, label) in enumerate(detected):
            node_id = f"preview_{agent}_{i}"
            branch_ids.append(node_id)
            nodes.append({
                "id": node_id, "type": "skill",
                "position": {"x": int(start_x + i * SPACING), "y": 170},
                "data": {"label": label, "domain": agent, "instruction": instruction[:200]},
            })
            edges.append({"id": f"e-trigger-{node_id}", "source": "trigger", "target": node_id})

        join_id = "preview_consolidar"
        nodes.append({
            "id": join_id, "type": "skill",
            "position": {"x": CENTER_X, "y": 330},
            "data": {
                "label": "Informe de resumen", "domain": "billing",
                "instruction": f"Genera un informe ejecutivo resumiendo el estado actual del negocio: {instruction[:150]}. Incluye totales, alertas y próximos pasos.",
            },
        })
        for bid in branch_ids:
            edges.append({"id": f"e-{bid}-{join_id}", "source": bid, "target": join_id})

    return nodes, edges


# ── Helpers ──────────────────────────────────────────────────────────────────


def _build_ai_instruction(workflow: models.Workflow) -> str:
    action_config = workflow.action_config or {}
    instruction = action_config.get("instruction") or action_config.get("intent")
    return instruction or workflow.description or workflow.name or "Ejecutar automatizacion"


def _infer_domain(workflow: models.Workflow) -> str:
    action_config = workflow.action_config or {}
    if action_config.get("agent") == "coordinator":
        return "coordinator"
    return "orchestrator"
