"""
Sub-módulo del orquestador: funciones que construyen contexto de ejecución
(estado inicial, carga de tarea, contexto de tenant, streaming, approval/invoice).
"""

import asyncio
import logging
import traceback
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.db.models.auth import Tenant
from app.db.models.models import (
    Client,
    Invoice,
    InvoiceLine,
    PendingApproval,
    Task,
)
from app.services.exec_log_store import push as log_push

logger = logging.getLogger(__name__)

# Nodos del orquestador cuyos nombres se emiten al frontend vía WebSocket
_ORCHESTRATOR_NODES = frozenset(
    {"init_tenant", "classify", "load_knowledge", "planner", "validate", "dispatch", "summarize"}
)


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
    task_uuid = uuid.UUID(task_id) if isinstance(task_id, str) else task_id
    result = await db.execute(select(Task).where(Task.id == task_uuid))
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

    # Si el usuario hizo /instruct a un AIEmployee específico, ese employee
    # tiene un domain concreto (hr, marketing, billing...). El endpoint
    # /instruct setea task.domain="coordinator" genérico pero guarda el
    # domain real en additional_metadata.addressed_employee_domain.
    # Preferimos ese domain real para evitar que el classify_node trate la
    # task como genérica y la pase al planner LLM (bug 5A de descomposición).
    _meta = task.additional_metadata or {}
    _addressed_dom = _meta.get("addressed_employee_domain")
    if _addressed_dom and task.domain == "coordinator":
        _initial_domain = _addressed_dom
    else:
        _initial_domain = task.domain if task.domain else None

    return {
        "task_id": task_id,
        "tenant_id": str(task.tenant_id),
        "user_id": str(task.created_by) if task.created_by else "",
        "user_intent": enriched_intent,
        "current_intent": None,
        "classified_domain": _initial_domain,
        "plan": None,
        "current_step": 0,
        "agent_results": [],
        "status": TaskStatus.PENDING,
        "requires_human_approval": False,
        "approval_id": None,
        "error_message": None,
        "iteration_count": 0,
        "tenant_knowledge": [],
        "additional_metadata": _meta,
    }


async def _broadcast(tenant_id: str, message: dict) -> None:
    """
    Envía un evento WebSocket al tenant.
    — Cuando REDIS_URL está configurado (modo Celery): publica en Redis pub/sub.
    — Sin Redis (modo in-process): llama directamente al WebSocket manager.
    """
    from app.core.config import settings

    if settings.REDIS_URL:
        import json as _json
        try:
            import redis.asyncio as aioredis
            async with aioredis.from_url(settings.REDIS_URL, decode_responses=True) as r:
                await r.publish(f"ap:ws:{tenant_id}", _json.dumps(message))
        except Exception:
            logger.debug("Error publicando evento en Redis", exc_info=True)
    else:
        from app.api.ws.notifications import manager as ws_manager
        await ws_manager.broadcast_to_tenant(tenant_id, message)


async def _stream_and_log(task_id: str, initial_state: dict, orchestrator) -> dict:
    """
    Ejecuta el grafo en modo streaming, emite logs por exec_log_store,
    transmite progreso por WebSocket y devuelve el estado final.
    """
    from app.core.llm_callbacks import UsageTrackingCallback, get_langfuse_callback

    final_state = None
    tenant_id = initial_state.get("tenant_id", "")
    domain = initial_state.get("classified_domain") or "unknown"
    seen_results: set = set()

    usage_callback = UsageTrackingCallback(tenant_id=tenant_id, agent_name=domain)
    callbacks: list = [usage_callback]
    langfuse_cb = get_langfuse_callback(
        tenant_id=tenant_id, agent=domain, task_id=task_id
    )
    if langfuse_cb is not None:
        callbacks.append(langfuse_cb)

    _run_config = {"recursion_limit": 50, "callbacks": callbacks}

    async def _run():
        nonlocal final_state
        try:
            async for chunk in orchestrator.astream(initial_state, config=_run_config):
                for node_name, state_update in chunk.items():
                    if node_name == "__end__":
                        final_state = state_update
                        continue
                    if state_update is None:
                        continue

                    # Notificar progreso de nodo al frontend
                    if node_name in _ORCHESTRATOR_NODES:
                        log_push(task_id, f"[{node_name}] completado")
                        await _broadcast(tenant_id, {
                            "type": "orchestrator_step",
                            "node": node_name,
                            "task_id": task_id,
                        })

                    for r in state_update.get("agent_results") or []:
                        rid = r.get("subtask_id") or r.get("agent", "") + str(len(seen_results))
                        if rid not in seen_results:
                            seen_results.add(rid)
                            agent = r.get("agent", "?")
                            summary = r.get("summary") or r.get("output", "")
                            if isinstance(summary, dict):
                                summary = summary.get("action") or str(summary)[:120]
                            ok = "OK" if r.get("success") else "FAIL"
                            log_push(task_id, f"[{ok}] [{agent}] {str(summary)[:200]}")
                            await _broadcast(tenant_id, {
                                "type": "agent_result",
                                "agent": agent,
                                "success": r.get("success", False),
                                "summary": str(summary)[:200],
                                "task_id": task_id,
                            })

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
        await asyncio.wait_for(_run(), timeout=900)
    except TimeoutError:
        logger.error("Timeout global (900s) en orquestador para tarea %s", task_id)
        # OrchestratorTimeoutError extiende Exception (NO TimeoutError) para que
        # _is_transient_error NO lo considere retry-able. Un cuelgue del LLM
        # interno no se cura reintentando con la misma instrucción — solo
        # acumula 900s+ de "executing" antes de fallar. Errores de red/BD
        # sí siguen siendo transient (ConnectionError, OSError).
        from app.core.exceptions import OrchestratorTimeoutError
        raise OrchestratorTimeoutError(
            f"Orquestador excedio el tiempo limite de 900s para tarea {task_id}"
        )

    result = final_state if final_state is not None else initial_state
    status_val = result.get("status")
    if hasattr(status_val, "value"):
        status_val = status_val.value
    log_push(
        task_id, f"[{'OK' if status_val == 'done' else 'FAIL'}] Ejecucion finalizada ({status_val})"
    )
    logger.info("FINAL STATE RETURNED BY LANGGRAPH: %s", result)
    return result, usage_callback


async def _load_task_and_approval(task_id: str, db):
    """
    Carga la tarea y el PendingApproval aprobado mas reciente.
    Devuelve (task, payload_dict) o None si falta alguno.
    """
    try:
        task_uuid = uuid.UUID(task_id) if isinstance(task_id, str) else task_id
        task_res = await db.execute(select(Task).where(Task.id == task_uuid))
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

    db.add(
        InvoiceLine(
            invoice_id=new_invoice.id,
            description=concept,
            quantity=Decimal("1"),
            unit_price=amount_base,
            tax_percentage=vat_rate,
            total=total_amount,
        )
    )
    await db.flush()

    # Actualizar tarea
    existing_results = list(task.agent_results or [])
    existing_results.append(
        {
            "agent": "billing",
            "success": True,
            "output": {
                "action": "draft_created",
                "local_invoice_id": str(new_invoice.id),
                "note": "Factura creada tras aprobacion manual.",
            },
        }
    )
    task.agent_results = existing_results
    task.current_step = task.current_step + 1
    task.status = "executing"
    task.requires_human_approval = False
    await db.commit()
    return True


async def _execute_from_approval(task, payload_data: dict, db) -> bool:
    """Ejecuta una acción retenida ESTRUCTURADA ({kind, params}) tras aprobación.

    Genérico para cualquier escritura financiera registrada en approval_actions
    (factura, asiento, nómina…). Reproduce el bookkeeping de
    `_create_invoice_from_approval`: ejecuta, añade un agent_result de éxito y
    avanza current_step para que el re-invoke del grafo no re-dispare el cap.
    """
    from app.services.workflow.approval_actions import execute_approved_action

    ok, summary = await execute_approved_action(payload_data, db, str(task.tenant_id))
    if not ok:
        task.status = "failed"
        task.error_message = summary
        await db.commit()
        return False

    existing_results = list(task.agent_results or [])
    existing_results.append(
        {
            "agent": payload_data.get("kind", "approval"),
            "success": True,
            "output": {"action": "executed_after_approval", "note": summary},
        }
    )
    task.agent_results = existing_results
    task.current_step = (task.current_step or 0) + 1
    task.status = "executing"
    task.requires_human_approval = False
    await db.commit()
    return True
