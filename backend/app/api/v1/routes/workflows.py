import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

_logger = logging.getLogger(__name__)

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.middleware.rate_limit import limiter

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
from app.api.v1.schemas import workflows as schemas
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import models
from app.services.node_engine import has_advanced_nodes

router = APIRouter(prefix="/workflows", tags=["Workflows & Automations"])

@router.get("/", response_model=list[schemas.WorkflowResponse])
@limiter.limit("30/minute")
async def list_workflows(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los workflows del tenant actual."""
    result = await db.execute(
        select(models.Workflow).where(models.Workflow.tenant_id == current_user.tenant_id)
    )
    return result.scalars().all()


@router.get("/recent-completions")
@limiter.limit("30/minute")
async def recent_completions(
    request: Request,
    since: float = Query(default=0.0, description="Unix timestamp; return executions completed after this time"),
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve las ejecuciones de workflow completadas/fallidas recientemente (para toast global)."""
    since_dt = (
        datetime.fromtimestamp(since, tz=timezone.utc)
        if since > 0
        else datetime.now(timezone.utc)
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
            models.WorkflowExecution.tenant_id == current_user.tenant_id,
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


@router.post("/", response_model=schemas.WorkflowResponse, status_code=201)
@limiter.limit("30/minute")
async def create_workflow(
    request: Request,
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
@limiter.limit("30/minute")
async def get_workflow(
    request: Request,
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
@limiter.limit("30/minute")
async def update_workflow(
    request: Request,
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
@limiter.limit("30/minute")
async def delete_workflow(
    request: Request,
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
@limiter.limit("30/minute")
async def run_workflow_manually(
    request: Request,
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

    # Bloquear ejecución simultánea: si ya hay una running/pending, rechazar
    existing = await db.execute(
        select(models.WorkflowExecution).where(
            models.WorkflowExecution.workflow_id == workflow_id,
            models.WorkflowExecution.status.in_(["running", "pending"]),
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=409,
            detail="Este workflow ya tiene una ejecución en curso. Espera a que termine antes de lanzarlo de nuevo."
        )

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
    if workflow.ui_nodes and has_advanced_nodes(workflow.ui_nodes, workflow.ui_edges):
        try:
            from app.services.task_dispatch import dispatch_node_engine
            await dispatch_node_engine(str(execution.id))
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
        from app.services.task_dispatch import dispatch_orchestrator
        await dispatch_orchestrator(str(task.id))
        execution.result_log = f"Tarea IA lanzada [{str(task.id)[:8]}...]. El agente esta procesando la instruccion."
    except Exception as e:
        execution.result_log = f"Error al lanzar el orquestador: {e}"
        execution.status = "failed"

    await db.commit()
    await db.refresh(execution)
    return execution


@router.post("/{workflow_id}/executions/{execution_id}/cancel", response_model=schemas.WorkflowExecutionResponse)
@limiter.limit("30/minute")
async def cancel_execution(
    request: Request,
    workflow_id: UUID,
    execution_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancela una ejecución atascada en estado running."""
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
    if execution.status not in ("running", "paused"):
        raise HTTPException(status_code=400, detail=f"No se puede cancelar una ejecución en estado '{execution.status}'")

    from datetime import datetime, UTC
    execution.status = "failed"
    execution.result_log = "Cancelado manualmente por el usuario."
    execution.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(execution)
    return execution


@router.post("/{workflow_id}/run-with-context", response_model=schemas.WorkflowExecutionResponse)
@limiter.limit("30/minute")
async def run_workflow_with_context(
    request: Request,
    workflow_id: UUID,
    body: dict,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ejecuta un workflow con contexto adicional proporcionado por el usuario."""
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

    context_msg = (body.get("context") or "").strip()
    base_instruction = _build_ai_instruction(workflow)
    full_instruction = f"{base_instruction}\n\nContexto adicional: {context_msg}" if context_msg else base_instruction

    execution = models.WorkflowExecution(
        workflow_id=workflow.id,
        tenant_id=current_user.tenant_id,
        status="running",
        trigger_payload={"source": "manual_with_context", "user_id": str(current_user.id), "context": context_msg}
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    task = models.Task(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        domain=_infer_domain(workflow),
        user_intent=full_instruction,
        status="pending",
        additional_metadata={"workflow_id": str(workflow.id), "execution_id": str(execution.id)},
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    execution.task_id = task.id
    await db.commit()

    try:
        from app.services.task_dispatch import dispatch_orchestrator
        await dispatch_orchestrator(str(task.id))
        execution.result_log = f"Tarea IA lanzada con contexto [{str(task.id)[:8]}...]."
    except Exception as e:
        execution.result_log = f"Error al lanzar: {e}"
        execution.status = "failed"

    await db.commit()
    await db.refresh(execution)
    return execution


@router.post("/{workflow_id}/executions/{execution_id}/resume", response_model=schemas.WorkflowExecutionResponse)
@limiter.limit("30/minute")
async def resume_execution(
    request: Request,
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
        from app.services.task_dispatch import dispatch_resume_node_engine
        await dispatch_resume_node_engine(str(execution_id), execution.current_node_id)
        execution.result_log = f"Reanudación programada desde nodo {execution.current_node_id}."
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al programar la reanudación: {e}")

    await db.commit()
    await db.refresh(execution)
    return execution


@router.get("/{workflow_id}/executions/{execution_id}/logs")
@limiter.limit("30/minute")
async def get_execution_logs(
    request: Request,
    workflow_id: UUID,
    execution_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve los logs de una ejecución."""
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

    lines: list[str] = []

    # Intentar exec_log_store primero (logs en tiempo real)
    if execution.task_id:
        try:
            from app.services.exec_log_store import get_all
            stored_lines = get_all(str(execution.task_id))
            if stored_lines:
                lines = stored_lines
        except Exception:
            _logger.debug("exec_log_store unavailable, using result_log fallback", exc_info=True)

    # Fallback: result_log de la ejecución
    if not lines and execution.result_log:
        lines = [execution.result_log]

    return {"lines": lines, "status": execution.status}


@router.get("/{workflow_id}/executions", response_model=list[schemas.WorkflowExecutionResponse])
@limiter.limit("30/minute")
async def get_workflow_executions(
    request: Request,
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
@limiter.limit("30/minute")
async def parse_natural_language_workflow(
    request: Request,
    body: schemas.WorkflowParseRequest,
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
    llm_plain = get_llm(temperature=0)

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
Events soportados: invoice_created, invoice_paid, client_created, document_uploaded, any.
(usa "any" si el usuario no especifica).''')

    try:
        response = llm.invoke([sys_msg, HumanMessage(content=body.text)])
        raw = response.content.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]
        payload = json.loads(raw.strip())

        # Segunda llamada enfocada: ¿puede ser determinista?
        can_det = False
        try:
            instruction = payload.get("action_config", {}).get("instruction", body.text)
            det_response = llm_plain.invoke([
                SystemMessage(content=(
                    "Responde ÚNICAMENTE con 'true' o 'false', sin ningún texto adicional.\n"
                    "Pregunta: ¿Puede esta acción ejecutarse siempre como una secuencia fija de pasos "
                    "sin necesidad de análisis, decisión o adaptación al contexto en cada ejecución?\n"
                    "Ejemplos true: enviar email fijo, generar informe estándar, exportar a Excel, crear factura con datos fijos.\n"
                    "Ejemplos false: analizar y decidir, revisar y responder según contenido, evaluar situación."
                )),
                HumanMessage(content=instruction),
            ])
            can_det = det_response.content.strip().lower().startswith("true")
        except Exception as det_err:
            import logging
            logging.getLogger(__name__).warning("Fallo detección determinismo: %s", det_err)
        payload["can_be_deterministic"] = can_det

        preview_nodes, preview_edges = _generate_preview_nodes(payload)
        payload["ui_nodes"] = preview_nodes
        payload["ui_edges"] = preview_edges
        return schemas.WorkflowParseResponse(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo parsear la regla: {str(e)}")


# ─── Endpoint para disparar desde eventos ERP ────────────────────────────────

@router.post("/fire-event")
@limiter.limit("30/minute")
async def fire_workflow_event(
    request: Request,
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

        execution = models.WorkflowExecution(
            workflow_id=wf.id,
            tenant_id=current_user.tenant_id,
            status="running",
            trigger_payload={"event": event_name, "context": context},
        )
        db.add(execution)
        await db.flush()

        # ── Ruta DETERMINISTA: pasos híbridos sin LLM ──
        if wf.execution_mode == "deterministic" and wf.compiled_steps:
            det_task = models.Task(
                tenant_id=current_user.tenant_id,
                created_by=current_user.id,
                domain="deterministic",
                user_intent=f"[Determinista] {wf.name} ({event_name})",
                status="running",
                additional_metadata={"workflow_id": str(wf.id), "execution_id": str(execution.id), "event": event_name},
            )
            db.add(det_task)
            await db.flush()
            execution.task_id = det_task.id

            try:
                results = await _execute_deterministic_steps(
                    steps=wf.compiled_steps,
                    tenant_id=str(current_user.tenant_id),
                    user_id=str(current_user.id),
                    task_id=str(det_task.id),
                )
                execution.status = "success"
                execution.result_log = (
                    f"Evento {event_name} → {len(results)} paso(s) deterministas. "
                    + " | ".join(
                        f"[{r.get('agent','?')}:{r.get('type','?')}] "
                        f"{'OK' if r.get('success') else 'ERR'}"
                        for r in results
                    )
                )
                det_task.status = "done"
                triggered.append(str(wf.id))
            except Exception as e:
                execution.status = "failed"
                execution.result_log = str(e)
                det_task.status = "failed"
            await db.commit()

        # ── Ruta REASONING: orquestador clásico ──
        else:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            ai_instruction = f"{_build_ai_instruction(wf)} [Contexto: {event_name} - {context_str}]"

            task = models.Task(
                tenant_id=current_user.tenant_id,
                created_by=current_user.id,
                domain=_infer_domain(wf),
                user_intent=ai_instruction,
                status="pending",
                additional_metadata={"workflow_id": str(wf.id), "execution_id": str(execution.id), "event": event_name},
            )
            db.add(task)
            await db.flush()
            execution.task_id = task.id
            await db.commit()
            await db.refresh(task)

            try:
                from app.services.task_dispatch import dispatch_orchestrator
                await dispatch_orchestrator(str(task.id))
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

    CENTER_X = 300
    nodes = [{
        "id": "trigger",
        "type": "trigger",
        "position": {"x": CENTER_X, "y": 0},
        "data": {"label": TRIGGER_LABELS.get(trigger_type, "Trigger"), "trigger_type": trigger_type},
    }]
    edges = []

    if len(detected) <= 1:
        # Single agent — simple linear layout
        agent, label = detected[0]
        node_id = "preview_agent_0"
        nodes.append({
            "id": node_id, "type": "skill",
            "position": {"x": CENTER_X, "y": 160},
            "data": {"label": label, "domain": agent, "instruction": instruction[:200]},
        })
        edges.append({"id": f"e-trigger-{node_id}", "source": "trigger", "target": node_id})
    else:
        # Multiple agents — parallel fan-out from trigger, then join node
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

        # Join/consolidator node — uses billing domain (always has DB access, no files needed)
        join_id = "preview_consolidar"
        nodes.append({
            "id": join_id, "type": "skill",
            "position": {"x": CENTER_X, "y": 330},
            "data": {"label": "Informe de resumen", "domain": "billing",
                     "instruction": f"Genera un informe ejecutivo resumiendo el estado actual del negocio: {instruction[:150]}. Incluye totales, alertas y próximos pasos."},
        })
        for bid in branch_ids:
            edges.append({"id": f"e-{bid}-{join_id}", "source": bid, "target": join_id})

    return nodes, edges


async def _execute_deterministic_steps(
    steps: list[dict],
    tenant_id: str,
    user_id: str,
    task_id: str | None = None,
) -> list[dict]:
    """
    Ejecuta los pasos precompilados de un workflow híbrido.

    Cada paso tiene un campo 'type':
      - "deterministic" → llama directamente a la @tool function (0 tokens LLM)
      - "reasoning"     → pasa por el dispatcher + LangGraph (usa LLM)

    Si el paso no tiene 'type', se infiere: si tiene 'tool' → deterministic, sino → reasoning.
    Los resultados de pasos anteriores se inyectan como $prev en el siguiente paso.
    """
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
    from app.agents.tool_registry import call_tool

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
    prev_output = ""  # resultado del paso anterior, inyectable como $prev

    for idx, step in enumerate(steps):
        agent_name = step.get("agent", "")
        step_type = step.get("type", "deterministic" if step.get("tool") else "reasoning")

        # ── Paso DETERMINISTA: llamada directa a @tool, sin LLM ──
        if step_type == "deterministic":
            tool_name = step.get("tool", "")
            if not tool_name:
                results.append({"agent": agent_name, "step": idx, "type": "deterministic",
                                "success": False, "error": "Paso determinista sin campo 'tool'"})
                continue

            # Construir params, inyectando tenant_id y $prev
            tool_params = dict(step.get("params", {}))
            tool_params.setdefault("tenant_id", tenant_id)

            # Sustituir $prev en valores string
            for k, v in tool_params.items():
                if isinstance(v, str) and "$prev" in v:
                    tool_params[k] = v.replace("$prev", prev_output)

            try:
                output = call_tool(tool_name, tool_params)
                prev_output = output
                results.append({
                    "agent": agent_name, "step": idx, "type": "deterministic",
                    "tool": tool_name, "success": True, "output": output, "error": None,
                })
            except Exception as exc:
                results.append({"agent": agent_name, "step": idx, "type": "deterministic",
                                "tool": tool_name, "success": False, "error": str(exc)})

        # ── Paso REASONING: dispatcher + LangGraph + LLM ──
        else:
            intent = step.get("params", {}).get("intent", "")
            # Inyectar resultado anterior si hay $prev en el intent
            if "$prev" in intent:
                intent = intent.replace("$prev", prev_output)

            subtask = {
                "id": f"hybrid_{idx}_{agent_name}",
                "subtask_id": f"hybrid_{idx}_{agent_name}",
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
                results.append({"agent": agent_name, "step": idx, "type": "reasoning",
                                "success": False, "error": f"Agente '{agent_name}' no reconocido"})
                continue

            try:
                result = await dispatch_fn(base_state, subtask)  # type: ignore[arg-type]
                output_data = result.get("output", {})
                prev_output = output_data.get("response", "") if isinstance(output_data, dict) else str(output_data)
                results.append({
                    "agent": agent_name, "step": idx, "type": "reasoning",
                    "action": step.get("action", ""),
                    "success": result.get("success", False),
                    "output": output_data,
                    "error": result.get("error"),
                })
            except Exception as exc:
                results.append({"agent": agent_name, "step": idx, "type": "reasoning",
                                "success": False, "error": str(exc)})

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
