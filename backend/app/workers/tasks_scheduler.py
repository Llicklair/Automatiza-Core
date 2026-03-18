"""
Tareas Celery periódicas: workflows programados, facturas recurrentes, limpieza de ejecuciones.
"""
from datetime import UTC

from app.workers.celery_app import celery_app, run_async


@celery_app.task(name="check_scheduled_workflows")
def check_scheduled_workflows():
    """
    Tarea periódica (cada minuto) que evalúa qué workflows schedule_based
    deben ejecutarse ahora según su trigger_config.

    trigger_config esperado para schedule_based:
    {
        "frequency": "daily" | "weekly" | "monthly" | "hourly",
        "hour": 8,          # Para daily/weekly/monthly
        "minute": 0,
        "day_of_week": 0,   # 0=lunes ... 6=domingo (para weekly)
        "day_of_month": 1,  # Para monthly
        "instruction": "..."  # Alternativa a action_config.instruction
    }
    Si no hay trigger_config, se interpreta la instrucción en lenguaje natural.
    """
    return run_async(_check_scheduled_workflows())


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
                # ── Idempotencia: evitar disparar el mismo workflow dos veces en el mismo minuto ──
                idempotency_key = f"{wf.id}:{now_local.strftime('%Y%m%d%H%M')}"

                from app.services.idempotency import SyncIdempotencyGuard
                guard = SyncIdempotencyGuard(ttl=120)  # TTL 2 min: suficiente para el mismo minuto
                if guard.already_executed("workflow_beat", idempotency_key):
                    print(f"[IDEMPOTENCY] Workflow '{wf.name}' ya disparado este minuto. Skip.")
                    continue

                # Bloquear si ya hay una ejecución activa para este workflow
                existing_exec = await db.execute(
                    select(WorkflowExecution).where(
                        WorkflowExecution.workflow_id == wf.id,
                        WorkflowExecution.status.in_(["running", "pending"]),
                    )
                )
                if existing_exec.scalars().first():
                    print(f"[BEAT] Workflow '{wf.name}' ya tiene ejecución activa. Skip.")
                    continue

                print(f"[BEAT] Disparando workflow programado: '{wf.name}'")
                # Construir instrucción
                action_config = wf.action_config or {}
                instruction = (
                    action_config.get("instruction")
                    or config.get("instruction")
                    or wf.description
                    or wf.name
                )

                # Inferir dominio
                text = f"{wf.name} {wf.description or ''} {instruction}".lower()
                domain = action_config.get("domain") or _infer_domain_from_text(text)

                # Crear ejecución primero para obtener su ID
                execution = WorkflowExecution(
                    workflow_id=wf.id,
                    tenant_id=wf.tenant_id,
                    status="running",
                    trigger_payload={"source": "celery_beat", "scheduled_at": now.isoformat()},
                )
                db.add(execution)
                await db.flush()

                # Crear Task hija con execution_id en metadata
                task = Task(
                    tenant_id=wf.tenant_id,
                    created_by=None,
                    domain=domain,
                    user_intent=f"[Automatización programada] {instruction}",
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
                    from app.workers.tasks_orchestrator import run_orchestrator
                    run_orchestrator.delay(str(task.id))
                    guard.mark_executed("workflow_beat", idempotency_key)
                except Exception as e:
                    execution.status = "failed"
                    execution.result_log = f"Error al lanzar orchestrator: {e}"
                    guard.release("workflow_beat", idempotency_key)

        await db.commit()


def _should_run_now(config: dict, now) -> bool:
    """
    Evalúa si un workflow schedule_based debe ejecutarse en este momento basándose en una expresión cron.
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
        print(f"[CELERY_BEAT] Error parsing cron: {cron_expr} -> {e}")
        return False


@celery_app.task(name="process_recurring_invoices")
def process_recurring_invoices():
    """Tarea diaria (8:00) que genera facturas a partir de plantillas recurrentes vencidas."""
    return run_async(_process_recurring_invoices())


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
                print(f"[RECURRING] Error procesando plantilla {rec.id}: {e}")

        await db.commit()
        print(f"[RECURRING] {generated} facturas generadas automáticamente.")
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


# ─── Cleanup: ejecuciones atascadas ──────────────────────────────────────────

@celery_app.task(name="cleanup_stuck_executions")
def cleanup_stuck_executions():
    """Cada 10 min: marca como 'failed' ejecuciones en 'running' de más de 15 min."""
    return run_async(_cleanup_stuck_executions())


async def _cleanup_stuck_executions():
    from datetime import datetime, timedelta
    from sqlalchemy import select, update as sa_update
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
        print(f"[CLEANUP] {len(stuck)} ejecucion(es) atascada(s) marcadas como failed.")
        return {"cleaned": len(stuck)}
