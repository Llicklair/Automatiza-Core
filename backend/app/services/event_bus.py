"""
Event Bus — Sistema de eventos internos para disparar automatizaciones.

Cuando un agente o endpoint crea/modifica datos relevantes, llaman a
`emit_event(db, tenant_id, user_id, event_name, context)`.

Esto busca todos los Workflows activos con trigger_type='event_based' del tenant
que escuchen ese evento (o "any") y lanza una Task+WorkflowExecution para cada uno.

Eventos que se EMITEN hoy (triggers funcionales):
  - invoice_created      → cuando se crea una factura
  - invoice_paid         → cuando una factura pasa a estado 'paid'
  - client_created       → cuando se registra un nuevo cliente
  - employee_created     → cuando se da de alta un empleado
  - document_processed   → cuando un documento termina de procesarse/clasificarse
  - payroll_created      → cuando se genera una nómina individual
  - payrolls_bulk_created → cuando se genera un lote de nóminas
  - payrolls_approved    → cuando se aprueba un lote de nóminas
  - invoice_overdue      → factura vencida sin cobrar (chequeo diario de alertas)

Eventos PENDIENTES de cablear (no emitidos todavía; no usar como trigger):
  - document_uploaded    → hoy cubierto por document_processed
  - task_completed / task_failed → requiere enganche en el orquestador
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import DomainEvent, Task, Workflow, WorkflowExecution

_logger = logging.getLogger(__name__)


async def emit_event(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None,
    event_name: str,
    context: dict[str, Any] | None = None,
) -> list[str]:
    """Emite un evento de negocio, lo persiste y dispara los workflows asociados.

    ⚠️ CONTRATO TRANSACCIONAL: esta función hace `await db.commit()` sobre la
    sesión recibida — es necesario para que el DomainEvent + Task +
    WorkflowExecution persistan y el worker pueda cargar la Task que se despacha.
    Por tanto CONFIRMA TAMBIÉN cualquier cambio pendiente que el caller tuviera
    en `db`. Llama a emit_event SOLO cuando tus escrituras de negocio ya estén
    finalizadas (o pásale una sesión dedicada); NO la uses a mitad de una
    transacción que debas poder revertir luego. (Acoplamiento transaccional
    conocido — refactor a savepoint pendiente, ver
    docs/architecture/information-flow.md §6.)
    """
    context = context or {}

    # 1. Persistir el evento para trazabilidad (DDD) e histórico IA
    domain_event = DomainEvent(
        tenant_id=tenant_id, user_id=user_id, event_name=event_name, payload=context
    )
    db.add(domain_event)
    await db.flush()

    # 2. Buscar workflows activos, event_based, del mismo tenant
    result = await db.execute(
        select(Workflow).where(
            Workflow.tenant_id == tenant_id,
            Workflow.is_active.is_(True),
            Workflow.trigger_type == "event_based",
        )
    )
    workflows = result.scalars().all()

    triggered_ids: list[str] = []

    from app.services.workflow.conditions import evaluate_conditions

    for wf in workflows:
        wf_config = wf.trigger_config or {}
        wf_events: list[str] = wf_config.get("events", [])

        # Escuchar el evento concreto o "any" (comodín)
        if event_name not in wf_events and "any" not in wf_events:
            continue

        # Evaluar conditions (gt, lt, eq, contains, AND/OR/NOT). Sin esto, un
        # workflow con condition "amount > 5000" se disparaba para CUALQUIER
        # invoice_created, ignorando el filtro y saturando el sistema.
        if not evaluate_conditions(wf_config.get("conditions"), context):
            _logger.debug(
                "[EVENT_BUS] Workflow '%s' bloqueado por conditions no cumplidas.", wf.name
            )
            continue

        # 3. Construir instrucción IA enriquecida con el contexto del evento
        base_instruction = _build_instruction(wf)
        # Limitar contexto si es muy grande para no saturar el prompt
        safe_ctx = {
            k: v for k, v in context.items() if not isinstance(v, dict | list) or len(str(v)) < 200
        }
        ctx_str = ", ".join(f"{k}: {v}" for k, v in safe_ctx.items())

        full_instruction = (
            (
                f"Automatizacion '{wf.name}': {base_instruction}. "
                f"[Contexto: {event_name} -> {ctx_str}]"
            )
            if ctx_str
            else base_instruction
        )

        # 4. Crear la Task que procesará el Orquestador
        task = Task(
            tenant_id=tenant_id,
            created_by=user_id,
            domain=_infer_domain(wf, full_instruction),
            user_intent=full_instruction,
            status="pending",
        )
        db.add(task)
        await db.flush()

        # 5. Registrar la ejecución del workflow vinculado a la task
        execution = WorkflowExecution(
            workflow_id=wf.id,
            tenant_id=tenant_id,
            status="pending",
            task_id=task.id,
            trigger_payload={"event": event_name, "context": context},
        )
        db.add(execution)
        await db.flush()

        # Backlink: el TaskRunner _update_workflow_execution sincroniza
        # workflow_executions.status al completar la task SOLO si la task
        # tiene additional_metadata.execution_id. Sin esto, las executions
        # event-driven quedaban en `pending` aunque la task completara.
        task.additional_metadata = {
            "workflow_id": str(wf.id),
            "execution_id": str(execution.id),
            "event": event_name,
        }

        # 6. Disparar tarea de forma asíncrona
        try:
            from app.services.workflow.task_dispatch import dispatch_orchestrator

            # Fase 3 (RLS): propagamos tenant_id del workflow al worker.
            await dispatch_orchestrator(str(task.id), tenant_id=str(wf.tenant_id))
            triggered_ids.append(str(wf.id))
            _logger.info(
                "[EVENT_BUS] Evento '%s' -> workflow '%s' iniciado (Task %s)",
                event_name, wf.name, task.id,
            )
        except Exception as e:
            execution.status = "failed"
            execution.result_log = f"Error dispatch: {str(e)}"

    # Confirmamos cambios (DomainEvent + Task + Execution)
    await db.commit()

    # 7. Notificar via WebSocket (UI dinámica)
    try:
        from app.api.ws.notifications import manager
        from app.core.background import spawn

        spawn(
            manager.broadcast_to_tenant(
                str(tenant_id),
                {"type": "event", "event": event_name, "workflow_count": len(triggered_ids)},
            )
        )
    except Exception:
        _logger.debug("Failed to broadcast event notification via WebSocket", exc_info=True)

    return triggered_ids


def _build_instruction(workflow: Workflow) -> str:
    """Extrae la instrucción base del workflow."""
    action_config = workflow.action_config or {}
    return (
        action_config.get("instruction")
        or workflow.description
        or workflow.name
        or "Procesar automatización"
    )


def _infer_domain(workflow: Workflow, instruction: str = "") -> str:
    """Deduce el dominio o usa el 'coordinator' si parece complejo."""
    action_config = workflow.action_config or {}
    if domain := action_config.get("domain"):
        return domain

    # Si hay varios pasos implícitos en la instrucción, usar coordinator
    text = f"{workflow.name} {instruction}".lower()
    if any(w in text for w in ["luego", "despues", "y también", "y envia", "y guarda"]):
        return "coordinator"

    # Fallbacks clásicos
    if any(w in text for w in ["factura", "billing", "invoice"]):
        return "billing"
    if any(w in text for w in ["nómina", "nomina", "rrhh", "hr"]):
        return "hr"
    return "billing"
