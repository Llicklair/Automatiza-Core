"""
Tareas periodicas: workflows programados, facturas recurrentes, limpieza de ejecuciones.
Coroutines puras invocadas por APScheduler.
"""

import logging
import zoneinfo
from datetime import UTC, date, datetime, timedelta

from croniter import croniter
from sqlalchemy import select

from app.core.tenant_context import set_current_tenant, system_context
from app.db.base import AsyncSessionLocal
from app.db.models.models import Invoice, InvoiceLine, RecurringInvoice
from app.services.idempotency import IdempotencyGuard
from app.services.workflow import execute_deterministic_steps
from app.services.workflow.conditions import evaluate_conditions
from app.services.workflow.db_conditions import resolve_db_conditions
from app.services.workflow.scheduler import (
    create_execution,
    create_task_for_execution,
    get_active_scheduled_workflows,
    get_last_execution,
    get_stuck_executions,
    has_active_execution,
    mark_executions_failed,
)
from app.services.workflow.task_dispatch import dispatch_orchestrator

logger = logging.getLogger(__name__)

try:
    _MADRID_TZ = zoneinfo.ZoneInfo("Europe/Madrid")
except Exception:
    _MADRID_TZ = UTC


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _should_run_now(config: dict, now) -> bool:
    """Evalua si la expresion cron del config coincide con el minuto actual."""
    cron_expr = config.get("cron")
    if not cron_expr:
        return False
    try:
        past = now - timedelta(minutes=1)
        next_run = croniter(cron_expr, past).get_next(now.__class__)
        return (
            next_run.year == now.year
            and next_run.month == now.month
            and next_run.day == now.day
            and next_run.hour == now.hour
            and next_run.minute == now.minute
        )
    except Exception as e:
        logger.warning("[SCHEDULER] Error parsing cron: %s -> %s", cron_expr, e)
        return False


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


def _calc_line_totals(line: dict) -> tuple[float, float]:
    """Devuelve (base, tax) para una linea de factura recurrente."""
    base = float(line.get("quantity", 1)) * float(line.get("unit_price", 0))
    tax = base * (float(line.get("tax_percentage", 21)) / 100)
    return base, tax


async def _dispatch_workflow(
    db,
    wf,
    execution,
    trigger_source: str,
    guard=None,
    idempotency_key: str | None = None,
) -> None:
    """
    Crea la Task y ejecuta el workflow (determinista o reasoning).
    Actualiza execution.status y task.status segun el resultado.
    """
    label = trigger_source.replace("_", " ").title()
    meta = {
        "workflow_id": str(wf.id),
        "execution_id": str(execution.id),
        "trigger_type": trigger_source,
    }

    if wf.execution_mode == "deterministic" and wf.compiled_steps:
        task = await create_task_for_execution(
            db,
            wf,
            execution,
            domain="deterministic",
            user_intent=f"[{label}] {wf.name}",
            initial_status="running",
            meta=meta,
        )
        try:
            results = await execute_deterministic_steps(
                steps=wf.compiled_steps,
                tenant_id=str(wf.tenant_id),
                user_id=str(wf.created_by) if wf.created_by else "",
                task_id=str(task.id),
            )
            execution.status = "success"
            execution.result_log = f"{len(results)} paso(s). " + " | ".join(
                f"[{r.get('agent', '?')}] {'OK' if r.get('success') else 'ERROR: ' + str(r.get('error', ''))[:60]}"
                for r in results
            )
            task.status = "done"
            if guard and idempotency_key:
                await guard.mark_executed("workflow_beat", idempotency_key)
        except Exception as e:
            execution.status = "failed"
            execution.result_log = f"Error determinista: {e}"
            task.status = "failed"
            if guard and idempotency_key:
                await guard.release("workflow_beat", idempotency_key)

    else:
        action_config = wf.action_config or {}
        config = wf.trigger_config or {}
        instruction = (
            action_config.get("instruction")
            or config.get("instruction")
            or wf.description
            or wf.name
        )
        domain = action_config.get("domain") or _infer_domain_from_text(
            f"{wf.name} {wf.description or ''} {instruction}".lower()
        )
        task = await create_task_for_execution(
            db,
            wf,
            execution,
            domain=domain,
            user_intent=f"[{label}] {instruction}",
            initial_status="pending",
            meta=meta,
        )
        try:
            await dispatch_orchestrator(str(task.id))
            if guard and idempotency_key:
                await guard.mark_executed("workflow_beat", idempotency_key)
        except Exception as e:
            execution.status = "failed"
            execution.result_log = f"Error lanzando orchestrator: {e}"
            if guard and idempotency_key:
                await guard.release("workflow_beat", idempotency_key)


# ---------------------------------------------------------------------------
# Tareas publicas (invocadas por APScheduler)
# ---------------------------------------------------------------------------


async def check_scheduled_workflows():
    """Cada minuto: dispara workflows schedule_based cuyo cron coincide con ahora."""
    try:
        await _check_scheduled_workflows()
    except Exception as e:
        logger.error("[SCHEDULER] Error en check_scheduled_workflows: %s", e)


async def _check_scheduled_workflows():
    now = datetime.now(UTC)
    now_local = datetime.now(_MADRID_TZ)

    async with AsyncSessionLocal() as db:
        # Bootstrap multi-tenant: get_active_scheduled_workflows debe ver
        # workflows de todos los tenants. Bajo RLS esto requiere system_context().
        with system_context():
            scheduled = await get_active_scheduled_workflows(db)

        for wf in scheduled:
            if not _should_run_now(wf.trigger_config or {}, now_local):
                continue

            set_current_tenant(str(wf.tenant_id))
            idempotency_key = f"{wf.id}:{now_local.strftime('%Y%m%d%H%M')}"
            guard = IdempotencyGuard(ttl=120)
            if await guard.already_executed("workflow_beat", idempotency_key):
                logger.info("[IDEMPOTENCY] Workflow '%s' ya disparado este minuto. Skip.", wf.name)
                continue

            if await has_active_execution(db, wf.id):
                logger.info("[BEAT] Workflow '%s' ya tiene ejecucion activa. Skip.", wf.name)
                continue

            temporal_context = {
                "now_hour": now_local.hour,
                "now_minute": now_local.minute,
                "now_weekday": now_local.weekday(),  # 0=lunes … 6=domingo
                "now_day": now_local.day,
                "now_month": now_local.month,
            }
            eval_context = await resolve_db_conditions(
                wf.trigger_config.get("conditions"), wf.tenant_id, db, temporal_context
            )
            if not evaluate_conditions(wf.trigger_config.get("conditions"), eval_context):
                logger.debug(
                    "[BEAT] Workflow '%s' bloqueado por condiciones no cumplidas.", wf.name
                )
                continue

            logger.info("[BEAT] Disparando workflow programado: '%s'", wf.name)
            execution = await create_execution(
                db, wf, {"source": "apscheduler", "scheduled_at": now.isoformat()}
            )
            await _dispatch_workflow(db, wf, execution, "schedule_based", guard, idempotency_key)

        # Limpia el ContextVar para que el último tenant del loop no quede activo.
        set_current_tenant(None)
        await db.commit()


async def catchup_missed_workflows():
    """Al arrancar la app: dispara una vez cada workflow que perdio ejecuciones."""
    try:
        await _catchup_missed_workflows()
    except Exception as e:
        logger.error("[CATCHUP] Error en catchup_missed_workflows: %s", e)


async def _catchup_missed_workflows():
    now_utc = datetime.now(UTC)
    now_local = datetime.now(_MADRID_TZ)

    async with AsyncSessionLocal() as db:
        with system_context():
            scheduled = await get_active_scheduled_workflows(db)

        for wf in scheduled:
            cron_expr = (wf.trigger_config or {}).get("cron")
            if not cron_expr:
                continue

            set_current_tenant(str(wf.tenant_id))
            last_exec = await get_last_execution(db, wf.id)
            since = last_exec.started_at if last_exec else wf.created_at
            if since.tzinfo is None:
                since = since.replace(tzinfo=UTC)

            since = max(since, now_utc - timedelta(days=7))
            since_local = since.astimezone(_MADRID_TZ)

            try:
                next_run = croniter(cron_expr, since_local).get_next(datetime)
            except Exception as e:
                logger.warning("[CATCHUP] Cron invalido '%s' en wf '%s': %s", cron_expr, wf.name, e)
                continue

            if next_run > now_local:
                continue

            logger.info(
                "[CATCHUP] Workflow '%s' perdio ejecucion(es) desde %s. Disparando una vez.",
                wf.name,
                since_local,
            )

            if await has_active_execution(db, wf.id):
                logger.info("[CATCHUP] Workflow '%s' ya tiene ejecucion activa. Skip.", wf.name)
                continue

            execution = await create_execution(
                db, wf, {"source": "catchup", "since": since.isoformat()}
            )
            await _dispatch_workflow(db, wf, execution, "catchup")

        set_current_tenant(None)
        await db.commit()


async def process_recurring_invoices():
    """Tarea diaria (8:00) que genera facturas a partir de plantillas recurrentes vencidas."""
    try:
        return await _process_recurring_invoices()
    except Exception as e:
        logger.error("[SCHEDULER] Error en process_recurring_invoices: %s", e)


async def _process_recurring_invoices():
    today = date.today()
    now = datetime.now(UTC)
    interval_map = {"weekly": 7, "monthly": 30, "quarterly": 90, "yearly": 365}

    async with AsyncSessionLocal() as db:
        # Bootstrap multi-tenant: la consulta carga RecurringInvoice de todos
        # los tenants vencidos. Bajo RLS necesita system_context().
        with system_context():
            result = await db.execute(
                select(RecurringInvoice).where(
                    RecurringInvoice.is_active.is_(True),
                    RecurringInvoice.next_run_date <= today,
                )
            )
            recurring = list(result.scalars().all())

        generated = 0
        for rec in recurring:
            try:
                set_current_tenant(str(rec.tenant_id))
                line_totals = [_calc_line_totals(ln) for ln in (rec.lines_json or [])]
                amount_base = sum(b for b, _ in line_totals)
                tax_amount = sum(t for _, t in line_totals)

                invoice = Invoice(
                    tenant_id=rec.tenant_id,
                    client_id=rec.client_id,
                    invoice_number=f"REC-{now.strftime('%Y%m%d%H%M%S')}-{generated}",
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

                for line, (base, tax) in zip(rec.lines_json or [], line_totals):
                    db.add(
                        InvoiceLine(
                            invoice_id=invoice.id,
                            description=line.get("description", ""),
                            quantity=line.get("quantity", 1),
                            unit_price=line.get("unit_price", 0),
                            discount_percentage=0,
                            tax_percentage=line.get("tax_percentage", 21),
                            total=round(base + tax, 2),
                        )
                    )

                rec.last_run_date = today
                rec.next_run_date = today + timedelta(days=interval_map.get(rec.interval_type, 30))
                generated += 1
            except Exception as e:
                logger.error("[RECURRING] Error procesando plantilla %s: %s", rec.id, e)

        set_current_tenant(None)
        await db.commit()
        logger.info("[RECURRING] %d facturas generadas automaticamente.", generated)
        return {"generated": generated}


async def cleanup_stuck_executions():
    """Cada 10 min: marca como 'failed' ejecuciones en 'running' de mas de 15 min."""
    try:
        return await _cleanup_stuck_executions()
    except Exception as e:
        logger.error("[SCHEDULER] Error en cleanup_stuck_executions: %s", e)


async def _cleanup_stuck_executions():
    cutoff = datetime.now(UTC) - timedelta(minutes=15)

    # Tarea de mantenimiento: opera sobre ejecuciones de todos los tenants.
    # Bajo RLS requiere system_context() durante toda la operación.
    async with AsyncSessionLocal() as db, system_context():
        stuck = await get_stuck_executions(db, cutoff)
        if not stuck:
            return {"cleaned": 0}

        await mark_executions_failed(db, stuck, "[Auto-cancelado: timeout 15 min]")
        await db.commit()
        logger.info("[CLEANUP] %d ejecucion(es) atascada(s) marcadas como failed.", len(stuck))
        return {"cleaned": len(stuck)}
