"""
Tareas periodicas: workflows programados, facturas recurrentes, limpieza de ejecuciones.
Coroutines puras invocadas por APScheduler.
"""
import logging
from datetime import UTC

from app.services.idempotency import IdempotencyGuard
from app.services.task_dispatch import dispatch_orchestrator

logger = logging.getLogger(__name__)


async def check_scheduled_workflows():
    """
    Tarea periodica (cada minuto) que evalua que workflows schedule_based
    deben ejecutarse ahora segun su trigger_config.
    """
    try:
        await _check_scheduled_workflows()
    except Exception as e:
        logger.error("[SCHEDULER] Error en check_scheduled_workflows: %s", e)


async def _check_scheduled_workflows():
    from datetime import datetime

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Task, Workflow, WorkflowExecution

    now = datetime.now(UTC)
    # Usar hora de Madrid (UTC+1 / UTC+2)
    import zoneinfo
    try:
        madrid = zoneinfo.ZoneInfo("Europe/Madrid")
        now_local = datetime.now(madrid)
    except Exception:
        now_local = now

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Workflow).where(
                Workflow.is_active.is_(True),
                Workflow.trigger_type == "schedule_based",
            )
        )
        workflows = result.scalars().all()

        for wf in workflows:
            config = wf.trigger_config or {}
            if _should_run_now(config, now_local):
                # -- Idempotencia: evitar disparar el mismo workflow dos veces en el mismo minuto --
                idempotency_key = f"{wf.id}:{now_local.strftime('%Y%m%d%H%M')}"

                guard = IdempotencyGuard(ttl=120)  # TTL 2 min: suficiente para el mismo minuto
                if await guard.already_executed("workflow_beat", idempotency_key):
                    logger.info("[IDEMPOTENCY] Workflow '%s' ya disparado este minuto. Skip.", wf.name)
                    continue

                # Bloquear si ya hay una ejecucion activa para este workflow
                existing_exec = await db.execute(
                    select(WorkflowExecution).where(
                        WorkflowExecution.workflow_id == wf.id,
                        WorkflowExecution.status.in_(["running", "pending"]),
                    )
                )
                if existing_exec.scalars().first():
                    logger.info("[BEAT] Workflow '%s' ya tiene ejecucion activa. Skip.", wf.name)
                    continue

                logger.info("[BEAT] Disparando workflow programado: '%s'", wf.name)

                # Crear ejecucion
                execution = WorkflowExecution(
                    workflow_id=wf.id,
                    tenant_id=wf.tenant_id,
                    status="running",
                    trigger_payload={"source": "apscheduler", "scheduled_at": now.isoformat()},
                )
                db.add(execution)
                await db.flush()

                # ── Ruta DETERMINISTA: pasos híbridos sin orquestador LLM ──
                if wf.execution_mode == "deterministic" and wf.compiled_steps:
                    task = Task(
                        tenant_id=wf.tenant_id,
                        created_by=None,
                        domain="deterministic",
                        user_intent=f"[Determinista] {wf.name}",
                        status="running",
                        additional_metadata={
                            "workflow_id": str(wf.id),
                            "execution_id": str(execution.id),
                            "trigger_type": "schedule_based",
                        },
                    )
                    db.add(task)
                    await db.flush()
                    execution.task_id = task.id
                    await db.flush()

                    try:
                        from app.api.v1.routes.workflows import _execute_deterministic_steps
                        results = await _execute_deterministic_steps(
                            steps=wf.compiled_steps,
                            tenant_id=str(wf.tenant_id),
                            user_id=str(wf.created_by) if wf.created_by else "",
                            task_id=str(task.id),
                        )
                        execution.status = "success"
                        execution.result_log = (
                            f"Ejecución determinista: {len(results)} paso(s). "
                            + " | ".join(
                                f"[{r.get('agent','?')}:{r.get('type','?')}] "
                                f"{'OK' if r.get('success') else 'ERROR: ' + str(r.get('error',''))[:60]}"
                                for r in results
                            )
                        )
                        task.status = "done"
                        await guard.mark_executed("workflow_beat", idempotency_key)
                    except Exception as e:
                        execution.status = "failed"
                        execution.result_log = f"Error determinista: {e}"
                        task.status = "failed"
                        await guard.release("workflow_beat", idempotency_key)

                # ── Ruta REASONING: orquestador clásico con LLM ──
                else:
                    action_config = wf.action_config or {}
                    instruction = (
                        action_config.get("instruction")
                        or config.get("instruction")
                        or wf.description
                        or wf.name
                    )
                    text = f"{wf.name} {wf.description or ''} {instruction}".lower()
                    domain = action_config.get("domain") or _infer_domain_from_text(text)

                    task = Task(
                        tenant_id=wf.tenant_id,
                        created_by=None,
                        domain=domain,
                        user_intent=f"[Automatizacion programada] {instruction}",
                        status="pending",
                        additional_metadata={
                            "workflow_id": str(wf.id),
                            "execution_id": str(execution.id),
                            "trigger_type": "schedule_based",
                            "scheduled_at": now.isoformat(),
                        },
                    )
                    db.add(task)
                    await db.flush()
                    execution.task_id = task.id
                    await db.flush()

                    try:
                        await dispatch_orchestrator(str(task.id))
                        await guard.mark_executed("workflow_beat", idempotency_key)
                    except Exception as e:
                        execution.status = "failed"
                        execution.result_log = f"Error al lanzar orchestrator: {e}"
                        await guard.release("workflow_beat", idempotency_key)

        await db.commit()


def _should_run_now(config: dict, now) -> bool:
    """
    Evalua si un workflow schedule_based debe ejecutarse en este momento basandose en una expresion cron.
    """
    cron_expr = config.get("cron")
    if not cron_expr:
        # Fallback to old parsing if old config exists, or return False if broken
        return False

    try:
        from croniter import croniter
        from datetime import timedelta
        # Ensure we're checking if the current minute is a match.
        # croniter returns next matching sequence. We check if 'now' is a match
        # by seeing if checking a minute ago yields 'now'.
        past = now - timedelta(minutes=1)
        it = croniter(cron_expr, past)
        next_run = it.get_next(now.__class__)

        # We consider a match if the next_run is within the same minute as 'now'
        return next_run.year == now.year and \
               next_run.month == now.month and \
               next_run.day == now.day and \
               next_run.hour == now.hour and \
               next_run.minute == now.minute

    except Exception as e:
        logger.warning("[SCHEDULER] Error parsing cron: %s -> %s", cron_expr, e)
        return False


async def process_recurring_invoices():
    """Tarea diaria (8:00) que genera facturas a partir de plantillas recurrentes vencidas."""
    try:
        return await _process_recurring_invoices()
    except Exception as e:
        logger.error("[SCHEDULER] Error en process_recurring_invoices: %s", e)


async def _process_recurring_invoices():
    import datetime as dt_module
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Invoice, InvoiceLine, RecurringInvoice

    today = dt_module.date.today()
    now = dt_module.datetime.now(dt_module.timezone.utc)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RecurringInvoice).where(
                RecurringInvoice.is_active.is_(True),
                RecurringInvoice.next_run_date <= today,
            )
        )
        due = result.scalars().all()
        generated = 0

        for rec in due:
            try:
                invoice_number = f"REC-{now.strftime('%Y%m%d%H%M%S')}-{generated}"
                amount_base = 0.0
                tax_amount = 0.0
                for line in (rec.lines_json or []):
                    base = float(line.get("quantity", 1)) * float(line.get("unit_price", 0))
                    tax = base * (float(line.get("tax_percentage", 21)) / 100)
                    amount_base += base
                    tax_amount += tax

                invoice = Invoice(
                    tenant_id=rec.tenant_id,
                    client_id=rec.client_id,
                    invoice_number=invoice_number,
                    date=now,
                    status="draft",
                    invoice_type="issued",
                    notes=rec.notes,
                    terms=rec.terms,
                    amount_base=round(amount_base, 2),
                    tax_amount=round(tax_amount, 2),
                    amount_total=round(amount_base + tax_amount, 2),
                )
                db.add(invoice)
                await db.flush()

                for line in (rec.lines_json or []):
                    base = float(line.get("quantity", 1)) * float(line.get("unit_price", 0))
                    tax = base * (float(line.get("tax_percentage", 21)) / 100)
                    inv_line = InvoiceLine(
                        invoice_id=invoice.id,
                        description=line.get("description", ""),
                        quantity=line.get("quantity", 1),
                        unit_price=line.get("unit_price", 0),
                        discount_percentage=0,
                        tax_percentage=line.get("tax_percentage", 21),
                        total=round(base + tax, 2),
                    )
                    db.add(inv_line)

                interval_map = {"weekly": 7, "monthly": 30, "quarterly": 90, "yearly": 365}
                days = interval_map.get(rec.interval_type, 30)
                rec.last_run_date = today
                rec.next_run_date = today + dt_module.timedelta(days=days)
                generated += 1

            except Exception as e:
                logger.error("[RECURRING] Error procesando plantilla %s: %s", rec.id, e)

        await db.commit()
        logger.info("[RECURRING] %d facturas generadas automaticamente.", generated)
        return {"generated": generated}


def _infer_domain_from_text(text: str) -> str:
    if any(w in text for w in ["factura", "cobro", "pago", "billing", "vencida", "invoice"]):
        return "billing"
    if any(w in text for w in ["empleado", "nomina", "nómina", "rrhh", "salario"]):
        return "hr"
    if any(w in text for w in ["cliente", "crm", "venta", "oportunidad"]):
        return "crm"
    if any(w in text for w in ["fiscal", "impuesto", "iva", "irpf", "aeat"]):
        return "advisory"
    if any(w in text for w in ["banco", "cuenta", "transferencia", "banking"]):
        return "banking"
    if any(w in text for w in ["documento", "archivo", "ocr", "contrato"]):
        return "documents"
    return "billing"


# --- Cleanup: ejecuciones atascadas ---

async def cleanup_stuck_executions():
    """Cada 10 min: marca como 'failed' ejecuciones en 'running' de mas de 15 min."""
    try:
        return await _cleanup_stuck_executions()
    except Exception as e:
        logger.error("[SCHEDULER] Error en cleanup_stuck_executions: %s", e)


async def _cleanup_stuck_executions():
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import WorkflowExecution

    cutoff = datetime.now(UTC) - timedelta(minutes=15)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.status == "running",
                WorkflowExecution.started_at < cutoff,
            )
        )
        stuck = result.scalars().all()
        if not stuck:
            return {"cleaned": 0}

        for ex in stuck:
            ex.status = "failed"
            ex.completed_at = datetime.now(UTC)
            ex.result_log = (ex.result_log or "") + " [Auto-cancelado: timeout 15 min]"

        await db.commit()
        logger.info("[CLEANUP] %d ejecucion(es) atascada(s) marcadas como failed.", len(stuck))
        return {"cleaned": len(stuck)}
