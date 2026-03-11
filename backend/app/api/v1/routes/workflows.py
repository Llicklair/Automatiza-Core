from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.v1.schemas import workflows as schemas
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import models

router = APIRouter(prefix="/workflows", tags=["Workflows & Automations"])

@router.get("/", response_model=list[schemas.WorkflowResponse])
async def list_workflows(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los workflows del tenant actual."""
    result = await db.execute(
        select(models.Workflow).where(models.Workflow.tenant_id == current_user.tenant_id)
    )
    return result.scalars().all()


@router.post("/", response_model=schemas.WorkflowResponse, status_code=201)
async def create_workflow(
    workflow_in: schemas.WorkflowCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Crea una nueva regla de automatización."""
    db_workflow = models.Workflow(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
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


@router.get("/{workflow_id}", response_model=schemas.WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el detalle de un workflow."""
    result = await db.execute(
        select(models.Workflow).where(
            models.Workflow.id == workflow_id,
            models.Workflow.tenant_id == current_user.tenant_id
        )
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    return workflow


@router.patch("/{workflow_id}", response_model=schemas.WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    workflow_in: schemas.WorkflowUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza una regla existente."""
    result = await db.execute(
        select(models.Workflow).where(
            models.Workflow.id == workflow_id,
            models.Workflow.tenant_id == current_user.tenant_id
        )
    )
    db_workflow = result.scalar_one_or_none()
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")

    update_data = workflow_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_workflow, key, value)

    await db.commit()
    await db.refresh(db_workflow)
    return db_workflow


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Elimina una regla de automatización."""
    result = await db.execute(
        select(models.Workflow).where(
            models.Workflow.id == workflow_id,
            models.Workflow.tenant_id == current_user.tenant_id
        )
    )
    db_workflow = result.scalar_one_or_none()
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
        
    await db.delete(db_workflow)
    await db.commit()
    return {"message": "Workflow eliminado correctamente"}


@router.post("/{workflow_id}/run", response_model=schemas.WorkflowExecutionResponse)
async def run_workflow_manually(
    workflow_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Ejecuta un workflow de forma manual via el orquestador AI o el motor de nodos."""
    result = await db.execute(
        select(models.Workflow).where(
            models.Workflow.id == workflow_id,
            models.Workflow.tenant_id == current_user.tenant_id
        )
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")

    if not workflow.is_active:
        raise HTTPException(status_code=400, detail="El workflow está desactivado")

    # 1. Registrar ejecución
    execution = models.WorkflowExecution(
        workflow_id=workflow.id,
        tenant_id=current_user.tenant_id,
        status="running",
        trigger_payload={"source": "manual_trigger", "user_id": str(current_user.id)}
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # 2. Detectar si tiene nodos avanzados → NodeEngine directo
    from app.services.node_engine import has_advanced_nodes
    if workflow.ui_nodes and has_advanced_nodes(workflow.ui_nodes, workflow.ui_edges):
        try:
            from app.workers.celery_app import run_node_engine
            run_node_engine.delay(str(execution.id))
            execution.result_log = f"Motor de nodos lanzado para ejecución [{str(execution.id)[:8]}...]."
        except Exception as e:
            execution.result_log = f"Error al lanzar el motor de nodos: {e}"
            execution.status = "failed"
        await db.commit()
        await db.refresh(execution)
        return execution

    # 3. Modo determinista → ejecutar pasos precompilados directamente
    if workflow.execution_mode == "deterministic" and workflow.compiled_steps:
        # Crear Task real en BD para que los agentes puedan guardar documentos
        det_task = models.Task(
            tenant_id=current_user.tenant_id,
            created_by=current_user.id,
            domain="deterministic",
            user_intent=f"[Determinista] {workflow.name}",
            status="running",
            additional_metadata={"workflow_id": str(workflow.id), "execution_id": str(execution.id)},
        )
        db.add(det_task)
        await db.flush()
        execution.task_id = det_task.id
        try:
            results = await _execute_deterministic_steps(
                steps=workflow.compiled_steps,
                tenant_id=str(current_user.tenant_id),
                user_id=str(current_user.id),
                task_id=str(det_task.id),
            )
            execution.status = "success"
            execution.result_log = (
                f"Ejecución determinista completada: {len(results)} paso(s). "
                + " | ".join(
                    f"[{r.get('agent', '?')}] {'OK' if r.get('success') else 'ERROR: ' + str(r.get('error',''))[:60]}"
                    for r in results
                )
            )
            det_task.status = "done"
        except Exception as e:
            execution.status = "failed"
            execution.result_log = f"Error en ejecución determinista: {e}"
            det_task.status = "failed"
        await db.commit()
        await db.refresh(execution)
        return execution

    # 4. Workflow simple → Orquestador clásico (modo 'reasoning')
    ai_instruction = _build_ai_instruction(workflow)
    task = models.Task(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        domain=_infer_domain(workflow),
        user_intent=ai_instruction,
        status="pending",
        additional_metadata={"workflow_id": str(workflow.id), "execution_id": str(execution.id)},
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    execution.task_id = task.id
    await db.commit()

    try:
        from app.workers.celery_app import run_orchestrator
        run_orchestrator.apply_async(args=[str(task.id)], task_id=str(task.id))
        execution.result_log = f"Tarea IA lanzada [{str(task.id)[:8]}...]. El agente esta procesando la instruccion."
    except Exception as e:
        execution.result_log = f"Error al lanzar el orquestador: {e}"
        execution.status = "failed"

    await db.commit()
    await db.refresh(execution)
    return execution


@router.post("/{workflow_id}/executions/{execution_id}/resume", response_model=schemas.WorkflowExecutionResponse)
async def resume_execution(
    workflow_id: UUID,
    execution_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reanuda una ejecución pausada (tras un approval gate)."""
    result = await db.execute(
        select(models.WorkflowExecution).where(
            models.WorkflowExecution.id == execution_id,
            models.WorkflowExecution.workflow_id == workflow_id,
            models.WorkflowExecution.tenant_id == current_user.tenant_id,
        )
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    if execution.status != "paused":
        raise HTTPException(status_code=400, detail=f"La ejecución no está pausada (estado: {execution.status})")
    if not execution.current_node_id:
        raise HTTPException(status_code=400, detail="No se puede determinar el nodo desde el que reanudar")

    try:
        from app.workers.celery_app import resume_node_engine
        resume_node_engine.delay(str(execution_id), execution.current_node_id)
        execution.result_log = f"Reanudación programada desde nodo {execution.current_node_id}."
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al programar la reanudación: {e}")

    await db.commit()
    await db.refresh(execution)
    return execution


@router.get("/{workflow_id}/executions", response_model=list[schemas.WorkflowExecutionResponse])
async def get_workflow_executions(
    workflow_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Devuelve el historial de ejecuciones de un workflow."""
    result = await db.execute(
        select(models.WorkflowExecution)
        .where(
            models.WorkflowExecution.workflow_id == workflow_id,
            models.WorkflowExecution.tenant_id == current_user.tenant_id,
        )
        .order_by(models.WorkflowExecution.started_at.desc())
        .limit(20)
    )
    return result.scalars().all()



@router.post("/parse-nl", response_model=schemas.WorkflowParseResponse)
async def parse_natural_language_workflow(
    request: schemas.WorkflowParseRequest,
    current_user: models.User = Depends(get_current_user),
):
    """
    Convierte un prompt de lenguaje natural en una configuración de Workflow (JSON).
    Usa el LLM para identificar si es event_based, schedule_based o manual.
    """
    import json

    from langchain_core.messages import HumanMessage, SystemMessage

    from app.core.llm_factory import get_llm

    llm = get_llm(temperature=0, format_output="json")
    
    sys_msg = SystemMessage(content='''Eres el Orquestador de Automatizaciones.
Dada una instrucción del usuario, devuelve ÚNICAMENTE un JSON válido con la configuración de la regla.
Format:
{
  "name": "Nombre corto y descriptivo",
  "description": "Explicación de qué hace",
  "trigger_type": "event_based" | "schedule_based" | "manual",
  "trigger_config": {"events": ["event_name"]} OR {"cron": "* * * * *"} OR {},
  "action_type": "ai_task",
  "action_config": {"instruction": "Instrucción exacta para el agente que se deba ejecutar"}
}

Events soportados: 
- invoice_created, invoice_paid, client_created, document_uploaded, any.
(usa "any" si el usuario no especifica).

Ejemplo 1: "Cuando se cobre una factura envia un email de agradecimiento"
-> trigger_type: event_based, trigger_config: {"events": ["invoice_paid"]}, action_config: {"instruction": "Envia email de agradecimiento al cliente."}

Ejemplo 2: "El dia 1 de cada mes genera el informe de balances"
-> trigger_type: schedule_based, trigger_config: {"cron": "0 0 1 * *"}, action_config: {"instruction": "Genera el informe de balances y guardalo."}
''')
    hum_msg = HumanMessage(content=request.text)
    
    try:
        response = llm.invoke([sys_msg, hum_msg])
        raw = response.content.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        
        payload = json.loads(raw)
        preview_nodes, preview_edges = _generate_preview_nodes(payload)
        payload["ui_nodes"] = preview_nodes
        payload["ui_edges"] = preview_edges
        return schemas.WorkflowParseResponse(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo parsear la regla: {str(e)}")


# ─── Endpoint para disparar desde eventos ERP ────────────────────────────────

@router.post("/fire-event")
async def fire_workflow_event(
    body: dict[str, Any],
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara todos los workflows activos con trigger 'event_based' que coincidan
    con el tipo de evento enviado.
    body = {"event": "invoice_created", "context": {...}}
    """
    event_name = body.get("event", "")
    context = body.get("context", {})

    result = await db.execute(
        select(models.Workflow).where(
            models.Workflow.tenant_id == current_user.tenant_id,
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

        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        ai_instruction = f"{_build_ai_instruction(wf)} [Contexto: {event_name} - {context_str}]"

        task = models.Task(
            tenant_id=current_user.tenant_id,
            created_by=current_user.id,
            domain=_infer_domain(wf),
            user_intent=ai_instruction,
            status="pending",
            additional_metadata={"workflow_id": str(wf.id), "event": event_name},
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        execution = models.WorkflowExecution(
            workflow_id=wf.id,
            tenant_id=current_user.tenant_id,
            status="running",
            task_id=task.id,
            trigger_payload={"event": event_name, "context": context},
        )
        db.add(execution)
        await db.commit()

        try:
            from app.workers.celery_app import run_orchestrator
            run_orchestrator.delay(str(task.id))
            triggered.append(str(wf.id))
        except Exception as e:
            execution.status = "failed"
            execution.result_log = str(e)
            await db.commit()

    return {"triggered_workflows": triggered, "event": event_name, "count": len(triggered)}


# ─── Helpers ────────────────────────────────────────────────────────────────

def _generate_preview_nodes(payload: dict) -> tuple[list, list]:
    """
    Genera una topología visual mínima (preview) a partir del payload parseado por IA.
    Devuelve (ui_nodes, ui_edges) para mostrar en el mapa antes de la primera ejecución real.
    """
    TRIGGER_LABELS = {
        "event_based": "Evento ERP", "schedule_based": "Programación", "manual": "Inicio Manual",
    }
    INSTRUCTION_TO_AGENT = [
        (["factura", "cobro", "pago", "billing", "invoice"], "billing", "Facturación"),
        (["empleado", "nómina", "nomina", "rrhh", "salario", "hr"], "hr", "RRHH"),
        (["cliente", "crm", "venta", "oportunidad", "contacto"], "crm", "CRM"),
        (["fiscal", "impuesto", "iva", "irpf", "aeat", "advisory"], "advisory", "Asesoría Fiscal"),
        (["banco", "cuenta", "transferencia", "banking"], "banking", "Banca"),
        (["documento", "archivo", "ocr", "contrato", "pdf"], "documents", "Documentos"),
        (["email", "correo", "envía", "envia", "notifica"], "email", "Email"),
        (["excel", "hoja", "informe", "reporte"], "excel", "Excel / Informe"),
    ]

    trigger_type = payload.get("trigger_type", "manual")
    instruction = (payload.get("action_config") or {}).get("instruction", "")
    description = payload.get("description", "")
    text = (instruction + " " + description).lower()

    # Detect agents from instruction keywords
    detected = []
    for keywords, agent, label in INSTRUCTION_TO_AGENT:
        if any(kw in text for kw in keywords):
            detected.append((agent, label))
    if not detected:
        detected = [("skill", "Agente IA")]

    nodes = [{
        "id": "trigger",
        "type": "trigger",
        "position": {"x": 250, "y": 0},
        "data": {"label": TRIGGER_LABELS.get(trigger_type, "Trigger"), "trigger_type": trigger_type},
    }]
    edges = []

    step_spacing = 130
    prev_id = "trigger"
    for i, (agent, label) in enumerate(detected):
        node_id = f"preview_{agent}_{i}"
        nodes.append({
            "id": node_id,
            "type": "skill",
            "position": {"x": 250, "y": 150 + i * step_spacing},
            "data": {"label": label, "domain": agent, "description": instruction[:100]},
        })
        edges.append({"id": f"e-{prev_id}-{node_id}", "source": prev_id, "target": node_id})
        prev_id = node_id

    return nodes, edges


async def _execute_deterministic_steps(
    steps: list[dict],
    tenant_id: str,
    user_id: str,
    task_id: str | None = None,
) -> list[dict]:
    """
    Ejecuta los pasos precompilados de un workflow determinista llamando directamente
    a las funciones _dispatch_* del orquestador con un estado mínimo.
    Devuelve una lista de resultados por paso.
    """
    from app.agents.orchestrator import (
        _dispatch_billing,
        _dispatch_crm,
        _dispatch_documents,
        _dispatch_email,
        _dispatch_excel,
        _dispatch_banking,
        _dispatch_hr,
        _dispatch_rag,
        _dispatch_compliance,
    )

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

    import uuid as _uuid
    # Estado mínimo compatible con OrchestratorState
    base_state: dict[str, Any] = {
        "task_id": task_id or str(_uuid.uuid4()),
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

    results = []
    for step in steps:
        agent_name = step.get("agent", "")
        intent = step.get("params", {}).get("intent", "")
        subtask = {
            "subtask_id": f"det_{agent_name}",
            "agent": agent_name,
            "action": step.get("action", ""),
            "params": {"intent": intent},
            "depends_on": [],
            "status": "pending",
        }
        base_state["user_intent"] = intent
        base_state["current_intent"] = intent

        dispatch_fn = _DISPATCH_MAP.get(agent_name)
        if dispatch_fn is None:
            results.append({"agent": agent_name, "success": False, "error": f"Agente '{agent_name}' no reconocido"})
            continue

        try:
            result = await dispatch_fn(base_state, subtask)  # type: ignore[arg-type]
            results.append({
                "agent": agent_name,
                "action": step.get("action", ""),
                "success": result.get("success", False),
                "output": result.get("output"),
                "error": result.get("error"),
            })
        except Exception as exc:
            results.append({"agent": agent_name, "success": False, "error": str(exc)})

    return results


def _build_ai_instruction(workflow: models.Workflow) -> str:
    action_config = workflow.action_config or {}
    # Soporta tanto "instruction" (nuevo) como "intent" (legacy) como fallback
    instruction = action_config.get("instruction") or action_config.get("intent")
    return instruction or workflow.description or workflow.name or "Ejecutar automatizacion"


def _infer_domain(workflow: models.Workflow) -> str:
    """
    Si el action_config indica explícitamente el agente coordinator,
    clasificamos directamente como coordinator para saltar el clasificador LLM.
    En cualquier otro caso, el orquestador clasifica.
    """
    action_config = workflow.action_config or {}
    if action_config.get("agent") == "coordinator":
        return "coordinator"
    return "orchestrator"
