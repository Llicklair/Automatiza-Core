"""
Tareas del orquestador LangGraph.
Coroutines puras ejecutadas por TaskRunner.
"""

import asyncio
import logging
import traceback
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.db.base import AsyncSessionLocal
from app.db.models.auth import Tenant
from app.db.models.models import (
    Client,
    Invoice,
    InvoiceLine,
    PendingApproval,
    Task,
    TenantDocument,
    Workflow as WFModel,
    WorkflowExecution as WFExec,
)
from app.services.exec_log_store import push as log_push
from app.services.idempotency import IdempotencyGuard

logger = logging.getLogger(__name__)


def _is_transient_error(exc: Exception) -> bool:
    """Devuelve True si el error es transitorio (red, timeout, rate limit)."""
    err_str = str(exc).lower()
    return (
        isinstance(exc, (ConnectionError, OSError, TimeoutError))
        or any(kw in err_str for kw in ("429", "rate limit", "timeout", "service unavailable", "overloaded", "connection"))
    )


async def _retry(label: str, task_id: str, fn, guard, *, attempts: int, backoff_base: int):
    """
    Ejecuta fn() con reintentos exponenciales.
    Marca la tarea como fallida y re-lanza si se agotan los intentos.
    """
    exc = None
    for attempt in range(attempts):
        countdown = backoff_base * (2 ** attempt)
        logger.warning("[RETRY] %s:%s intento %d/%d en %ds", label, task_id, attempt + 1, attempts, countdown)
        await asyncio.sleep(countdown)
        try:
            result = await fn()
            await guard.mark_executed(label, task_id, {"status": "done"})
            return result
        except Exception as retry_exc:
            logger.warning("[RETRY] %s:%s fallo intento %d: %s", label, task_id, attempt + 1, retry_exc)
            exc = retry_exc
    await _mark_task_failed(task_id, str(exc))
    raise exc


async def execute_orchestrator(task_id: str):
    """Ejecuta el orquestador LangGraph para una tarea dada."""
    guard = IdempotencyGuard()

    if await guard.already_executed("run_orchestrator", task_id):
        logger.info("[IDEMPOTENCY] run_orchestrator:%s ya ejecutado. Skip.", task_id)
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = await _execute_orchestrator(task_id)
        await guard.mark_executed("run_orchestrator", task_id, {"status": "done"})
        return result
    except Exception as exc:
        logger.exception("Error en run_orchestrator:%s", task_id)
        if _is_transient_error(exc):
            await guard.release("run_orchestrator", task_id)
            return await _retry("run_orchestrator", task_id, lambda: _execute_orchestrator(task_id), guard, attempts=3, backoff_base=30)
        await _mark_task_failed(task_id, str(exc))
        raise


async def resume_orchestrator(task_id: str):
    """Reanuda el orquestador tras una aprobacion humana."""
    guard = IdempotencyGuard()

    if await guard.already_executed("resume_orchestrator", task_id):
        logger.info("[IDEMPOTENCY] resume_orchestrator:%s ya ejecutado. Skip.", task_id)
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = await _resume_orchestrator(task_id)
        await guard.mark_executed("resume_orchestrator", task_id, {"status": "done"})
        return result
    except Exception as exc:
        logger.exception("Error en resume_orchestrator:%s", task_id)
        await guard.release("resume_orchestrator", task_id)
        return await _retry("resume_orchestrator", task_id, lambda: _resume_orchestrator(task_id), guard, attempts=3, backoff_base=10)


async def _mark_task_failed(task_id: str, error_msg: str):
    """Marca una tarea como fallida en BD directamente (sin pasar por el orquestador)."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Task).where(Task.id == task_id))
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
    task.status = (
        final_state["status"].value
        if hasattr(final_state["status"], "value")
        else final_state["status"]
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
    if not wf_exec or wf_exec.status != "running":
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


async def _build_tenant_context(tenant_id: str, db) -> str:
    """
    Carga contexto del tenant desde BD y lo devuelve como string para inyectar en el intent.
    Incluye: nombre empresa, NIF, fecha actual, primeros clientes disponibles.
    """
    lines = [f"Fecha actual: {date.today().strftime('%d/%m/%Y')}. Moneda: EUR. Pais: Espana."]

    try:
        tenant_res = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
        tenant = tenant_res.scalar_one_or_none()
        if tenant:
            lines.append(f"Empresa emisora: {tenant.name} (NIF: {tenant.nif}).")
    except Exception:
        logger.debug("Error cargando contexto tenant %s", tenant_id, exc_info=True)

    try:
        clients_res = await db.execute(
            select(Client)
            .where(Client.tenant_id == uuid.UUID(tenant_id))
            .order_by(Client.created_at.asc())
            .limit(5)
        )
        clients = clients_res.scalars().all()
        if clients:
            client_list = ", ".join(f"{c.name} (NIF: {c.nif})" for c in clients)
            lines.append(f"Clientes disponibles: {client_list}.")
    except Exception:
        logger.debug("Error cargando clientes para contexto tenant %s", tenant_id, exc_info=True)

    return " ".join(lines)


async def _load_and_start_task(task_id: str, db):
    """
    Carga la tarea, verifica que no este cancelada y la marca como executing.
    Devuelve la tarea o None si no debe continuar.
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return None

    if task.status == "cancelled":
        logger.info("Tarea %s fue cancelada antes de iniciar. Abortando.", task_id)
        return None

    task.status = "executing"
    task.started_at = datetime.now(UTC)
    await db.commit()
    return task


async def _build_initial_state(task, task_id: str, db) -> dict:
    """
    Construye el OrchestratorState inicial, enriqueciendo el intent con
    contexto del tenant cuando la tarea proviene de una automatizacion.
    """
    from app.agents.orchestrator import TaskStatus

    base_intent = task.user_intent or ""
    if (task.additional_metadata or {}).get("workflow_id"):
        try:
            ctx = await _build_tenant_context(str(task.tenant_id), db)
            enriched_intent = f"{base_intent}\n\n[Contexto del sistema: {ctx}]"
        except Exception:
            enriched_intent = base_intent
    else:
        enriched_intent = base_intent

    return {
        "task_id": task_id,
        "tenant_id": str(task.tenant_id),
        "user_id": str(task.created_by) if task.created_by else "",
        "user_intent": enriched_intent,
        "current_intent": None,
        "classified_domain": task.domain if task.domain else None,
        "plan": None,
        "current_step": 0,
        "agent_results": [],
        "status": TaskStatus.PENDING,
        "requires_human_approval": False,
        "approval_id": None,
        "error_message": None,
        "iteration_count": 0,
        "tenant_knowledge": [],
        "additional_metadata": task.additional_metadata or {},
    }


async def _stream_and_log(task_id: str, initial_state: dict, orchestrator) -> dict:
    """
    Ejecuta el grafo en modo streaming, emite logs por exec_log_store y
    devuelve el estado final.
    """
    final_state = None
    seen_results: set = set()

    async def _run():
        nonlocal final_state
        try:
            async for chunk in orchestrator.astream(
                initial_state, config={"recursion_limit": 50}
            ):
                for node_name, state_update in chunk.items():
                    if node_name == "__end__":
                        final_state = state_update
                        continue
                    if state_update is None:
                        continue

                    for r in (state_update.get("agent_results") or []):
                        rid = r.get("subtask_id") or r.get("agent", "") + str(len(seen_results))
                        if rid not in seen_results:
                            seen_results.add(rid)
                            agent = r.get("agent", "?")
                            summary = r.get("summary") or r.get("output", "")
                            if isinstance(summary, dict):
                                summary = summary.get("action") or str(summary)[:120]
                            ok = "OK" if r.get("success") else "FAIL"
                            log_push(task_id, f"[{ok}] [{agent}] {str(summary)[:200]}")

                    err = state_update.get("error_message")
                    if err and err not in seen_results:
                        seen_results.add(err)
                        log_push(task_id, f"[WARN] {err[:200]}")

                    if state_update.get("status") in ("done", "failed", "awaiting_approval"):
                        final_state = state_update
        except Exception as stream_exc:
            logger.exception("Excepcion en orchestrator.astream() para tarea %s", task_id)
            log_push(task_id, f"[ERROR] {type(stream_exc).__name__}: {stream_exc}")
            raise

    try:
        await asyncio.wait_for(_run(), timeout=300)
    except asyncio.TimeoutError:
        logger.error("Timeout global (300s) en orquestador para tarea %s", task_id)
        raise TimeoutError(f"Orquestador excedio el tiempo limite de 300s para tarea {task_id}")

    result = final_state if final_state is not None else initial_state
    status_val = result.get("status")
    if hasattr(status_val, "value"):
        status_val = status_val.value
    log_push(task_id, f"[{'OK' if status_val == 'done' else 'FAIL'}] Ejecucion finalizada ({status_val})")
    logger.info("FINAL STATE RETURNED BY LANGGRAPH: %s", result)
    return result


async def _execute_orchestrator(task_id: str):
    """Coordina: cargar tarea → construir estado → stream LangGraph → persistir."""
    from app.agents.orchestrator import orchestrator

    async with AsyncSessionLocal() as db:
        task = await _load_and_start_task(task_id, db)
        if not task:
            return

        initial_state = await _build_initial_state(task, task_id, db)

        log_push(task_id, "Iniciando automatizacion...")
        final_state = await _stream_and_log(task_id, initial_state, orchestrator)

        await _save_final_state(task, final_state, db)
        await _sync_workflow_artifacts(task, final_state, db)
        await db.commit()


async def _load_task_and_approval(task_id: str, db):
    """
    Carga la tarea y el PendingApproval aprobado mas reciente.
    Devuelve (task, payload_dict) o None si falta alguno.
    """
    try:
        task_res = await db.execute(select(Task).where(Task.id == task_id))
        task = task_res.scalar_one_or_none()
        if not task:
            logger.error("[RESUME] Tarea %s no encontrada", task_id)
            return None

        approval_res = await db.execute(
            select(PendingApproval)
            .where(
                PendingApproval.task_id == uuid.UUID(task_id),
                PendingApproval.status == "approved",
            )
            .order_by(PendingApproval.approved_at.desc())
            .limit(1)
        )
        approval = approval_res.scalars().first()

        if not approval or not approval.action_payload:
            logger.error("[RESUME] Approval no encontrado o sin payload para tarea %s", task_id)
            task.status = "failed"
            task.error_message = (
                "No se encontro la aprobacion asociada para continuar o el payload esta vacio."
            )
            await db.commit()
            return None

        logger.info("[RESUME] Payload cargado: keys=%s", list(approval.action_payload.keys()))
        return task, approval.action_payload

    except Exception as _e:
        logger.error("[RESUME] Error critico cargando tarea/approval: %s", _e)
        traceback.print_exc()
        return None


async def _create_invoice_from_approval(task, payload_data: dict, db) -> bool:
    """
    Resuelve el cliente, crea Invoice + InvoiceLine y avanza el paso de la tarea.
    Devuelve False si no se puede continuar.
    """
    client_nif = payload_data.get("client_nif")
    amount_base = Decimal(str(payload_data.get("amount_base", "0")).replace(",", "."))
    vat_rate = Decimal(str(payload_data.get("vat_rate", 21)))
    concept = payload_data.get("concept", "Concepto por aprobacion manual")
    inv_date = date.fromisoformat(
        payload_data.get("invoice_date", datetime.now(UTC).strftime("%Y-%m-%d"))
    )

    # Resolver cliente por ID o NIF
    cliente_local = None
    if "contact_id_local" in payload_data:
        res = await db.execute(
            select(Client).where(Client.id == uuid.UUID(payload_data["contact_id_local"]))
        )
        cliente_local = res.scalars().first()

    if not cliente_local and client_nif:
        res = await db.execute(
            select(Client).where(Client.tenant_id == task.tenant_id, Client.nif == client_nif)
        )
        cliente_local = res.scalars().first()

    # Fallback: crear cliente si no existe
    if not cliente_local and client_nif:
        logger.info("[RESUME] Cliente %s no existe, creando como fallback.", client_nif)
        cliente_local = Client(
            tenant_id=task.tenant_id,
            nif=client_nif,
            name=payload_data.get("client_name", "Cliente Generado Auto"),
        )
        db.add(cliente_local)
        await db.commit()
        await db.refresh(cliente_local)

    if not cliente_local:
        task.status = "failed"
        task.error_message = (
            "No se encontro ni se pudo crear el cliente local vinculado durante la reanudacion."
        )
        await db.commit()
        return False

    # Crear factura
    tax_amount = round(amount_base * (vat_rate / Decimal("100")), 2)
    total_amount = amount_base + tax_amount

    count_res = await db.execute(
        select(func.count(Invoice.id)).where(Invoice.tenant_id == task.tenant_id)
    )
    invoice_number = f"FAC-{inv_date.year}-{(count_res.scalar() or 0) + 1:04d}"

    new_invoice = Invoice(
        tenant_id=task.tenant_id,
        client_id=cliente_local.id,
        invoice_number=invoice_number,
        date=inv_date,
        amount_base=amount_base,
        tax_amount=tax_amount,
        amount_total=total_amount,
        status="draft",
        invoice_type="issued",
        external_id=None,
    )
    db.add(new_invoice)
    await db.flush()

    db.add(InvoiceLine(
        invoice_id=new_invoice.id,
        description=concept,
        quantity=Decimal("1"),
        unit_price=amount_base,
        tax_percentage=vat_rate,
        total=total_amount,
    ))
    await db.flush()

    # Actualizar tarea
    existing_results = list(task.agent_results or [])
    existing_results.append({
        "agent": "billing",
        "success": True,
        "output": {
            "action": "draft_created",
            "local_invoice_id": str(new_invoice.id),
            "note": "Factura creada tras aprobacion manual.",
        },
    })
    task.agent_results = existing_results
    task.current_step = task.current_step + 1
    task.status = "executing"
    task.requires_human_approval = False
    await db.commit()
    return True


async def _resume_orchestrator(task_id: str):
    """
    Reanuda la ejecucion despues de una aprobacion humana.
    Coordina: cargar tarea/approval → crear factura → re-invocar LangGraph.
    """
    from app.agents.orchestrator import OrchestratorState, TaskStatus, orchestrator

    async with AsyncSessionLocal() as db:
        result = await _load_task_and_approval(task_id, db)
        if not result:
            return
        task, payload_data = result

        ok = await _create_invoice_from_approval(task, payload_data, db)
        if not ok:
            return

        initial_state: OrchestratorState = {
            "task_id": task_id,
            "tenant_id": str(task.tenant_id),
            "user_id": str(task.created_by) if task.created_by else "",
            "user_intent": task.user_intent or "",
            "classified_domain": task.domain if task.domain else None,
            "plan": task.plan,
            "current_step": task.current_step,
            "agent_results": task.agent_results,
            "status": TaskStatus.EXECUTING,
            "requires_human_approval": False,
            "approval_id": None,
            "error_message": task.error_message,
            "iteration_count": 0,
            "additional_metadata": task.additional_metadata or {},
        }

        final_state = await orchestrator.ainvoke(initial_state, config={"recursion_limit": 50})

        await _save_final_state(task, final_state, db)
        await db.commit()
