"""
Tareas periodicas: workflows programados, facturas recurrentes, limpieza de ejecuciones.
Coroutines puras invocadas por APScheduler.
"""

import logging
import zoneinfo
from datetime import UTC, date, datetime, timedelta

from croniter import croniter
from sqlalchemy import select

from app.core.tenant_context import set_current_tenant
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


#: Tolerancia para ticks retrasados (suspensión del portátil, GC, DB lenta).
#: Si el tick llega hasta N minutos tarde, la ejecución perdida se recupera.
_GRACE_MINUTES = 10


def _next_due_run(config: dict, now) -> "datetime | None":
    """Devuelve el instante programado más reciente que esté vencido dentro
    de la ventana de gracia, o None si no toca ejecutar.

    Antes se exigía coincidencia exacta de minuto con el tick: cualquier
    retraso >60s perdía la ejecución sin error. Ahora un tick retrasado
    recupera la última ejecución vencida (una sola — sin ráfagas), y la
    clave de idempotencia se construye con el instante programado, no con
    el minuto del tick, para que no se dispare dos veces.
    """
    cron_expr = config.get("cron")
    if not cron_expr:
        return None
    try:
        it = croniter(cron_expr, now - timedelta(minutes=_GRACE_MINUTES))
        due = None
        candidate = it.get_next(now.__class__)
        while candidate <= now:
            due = candidate
            candidate = it.get_next(now.__class__)
        return due
    except Exception as e:
        logger.warning("[SCHEDULER] Error parsing cron: %s -> %s", cron_expr, e)
        return None


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
    # Sin match → "chat": el coordinador clasifica con LLM. Antes el default
    # era "billing" y cualquier workflow genérico acababa en facturación.
    return "chat"


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
            # Fase 3 (RLS): propagamos tenant_id explícito al dispatcher.
            await dispatch_orchestrator(str(task.id), tenant_id=str(wf.tenant_id))
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
        # Fase 3 (RLS): esta lectura inicial es CROSS-TENANT por diseño
        # (APScheduler es global, no atado a un tenant). El listener RLS
        # se desactiva temporalmente con set_current_tenant(None) y cada
        # workflow re-establece su tenant_id antes de cualquier operación
        # que toque datos del tenant.
        set_current_tenant(None)
        for wf in await get_active_scheduled_workflows(db):
            due_run = _next_due_run(wf.trigger_config or {}, now_local)
            if due_run is None:
                continue

            set_current_tenant(str(wf.tenant_id))
            # Clave por instante PROGRAMADO (no por minuto del tick): un tick
            # retrasado recupera la ejecución sin riesgo de dispararla dos veces.
            idempotency_key = f"{wf.id}:{due_run.strftime('%Y%m%d%H%M')}"
            guard = IdempotencyGuard(ttl=(_GRACE_MINUTES + 5) * 60)
            if await guard.already_executed("workflow_beat", idempotency_key):
                logger.debug("[IDEMPOTENCY] Workflow '%s' ya disparado (%s). Skip.", wf.name, idempotency_key)
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
        # Fase 3 (RLS): lectura inicial cross-tenant intencionada (catchup
        # es global). Cada iteración fija set_current_tenant antes de
        # operar sobre datos del tenant correspondiente.
        set_current_tenant(None)
        for wf in await get_active_scheduled_workflows(db):
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
        # Fase 3 (RLS): lectura inicial cross-tenant intencionada (este job
        # diario abarca todas las plantillas recurrentes de todos los tenants).
        # Antes de generar cada Invoice se fija set_current_tenant(rec.tenant_id)
        # dentro del loop.
        set_current_tenant(None)
        result = await db.execute(
            select(RecurringInvoice).where(
                RecurringInvoice.is_active.is_(True),
                RecurringInvoice.next_run_date <= today,
            )
        )
        generated = 0
        for rec in result.scalars().all():
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

    async with AsyncSessionLocal() as db:
        stuck = await get_stuck_executions(db, cutoff)
        if not stuck:
            return {"cleaned": 0}

        await mark_executions_failed(db, stuck, "[Auto-cancelado: timeout 15 min]")
        await db.commit()
        logger.info("[CLEANUP] %d ejecucion(es) atascada(s) marcadas como failed.", len(stuck))
        return {"cleaned": len(stuck)}


# Reintentos automáticos de publicación con backoff exponencial.
_MAX_PUBLISH_RETRIES = 5
_RETRY_BASE_MINUTES = 5  # delays: 5, 10, 20, 40, 80 min


def _handle_publish_result(post, result, now: datetime) -> str:
    """Decide qué hacer con un post tras intentar publicarlo.

    Devuelve "published" | "retried" | "failed" y muta el post en consecuencia.
    Un fallo transitorio con reintentos disponibles vuelve a 'scheduled' con
    `scheduled_at` empujado por backoff; agotados o permanente queda 'failed'.
    """
    if result.ok:
        return "published"
    if result.transient and post.retry_count < _MAX_PUBLISH_RETRIES:
        post.retry_count += 1
        delay = _RETRY_BASE_MINUTES * (2 ** (post.retry_count - 1))
        post.status = "scheduled"
        post.scheduled_at = now + timedelta(minutes=delay)
        post.error_message = (
            f"Reintento {post.retry_count}/{_MAX_PUBLISH_RETRIES} en {delay} min: "
            f"{post.error_message or ''}"
        )[:500]
        return "retried"
    return "failed"


async def publish_scheduled_posts():
    """Cada 5 min: publica posts con status='scheduled' y scheduled_at <= ahora."""
    try:
        await _publish_scheduled_posts()
    except Exception as e:
        logger.error("[MARKETING] Error en publish_scheduled_posts: %s", e)


async def _publish_scheduled_posts():
    from app.db.models.marketing import ScheduledPost
    from app.services.marketing.publishing import get_publisher

    publisher = get_publisher()
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        set_current_tenant(None)
        result = await db.execute(
            select(ScheduledPost)
            .where(
                ScheduledPost.status == "scheduled",
                ScheduledPost.scheduled_at <= now,
            )
            .limit(20)
        )
        posts = result.scalars().all()
        published = retried = 0
        for post in posts:
            set_current_tenant(str(post.tenant_id))
            outcome = _handle_publish_result(post, await publisher.publish_post(post, db), now)
            if outcome == "published":
                published += 1
            elif outcome == "retried":
                retried += 1
        set_current_tenant(None)
        await db.commit()
        if posts:
            logger.info(
                "[MARKETING] %d publicados, %d reprogramados, %d fallidos (de %d).",
                published, retried, len(posts) - published - retried, len(posts),
            )


async def check_failed_workflow_executions():
    """Cada 10 min: notifica al gestor las ejecuciones de workflow que fallaron.

    Las automatizaciones programadas/por-evento corren desatendidas: si fallan
    en silencio (el bug #1 que mata el producto fiscal), el gestor nunca se
    entera. Este sweep detecta cualquier ejecución `failed` aún sin notificar y
    crea una notificación de error. Las manuales NO avisan (el usuario las está
    viendo en la UI). El flag `notified` evita avisar dos veces.
    """
    try:
        await _check_failed_workflow_executions()
    except Exception as e:
        logger.error("[ALERTS] Error en check_failed_workflow_executions: %s", e)


async def _check_failed_workflow_executions():
    from sqlalchemy.orm import selectinload

    from app.db.models.models import WorkflowExecution
    from app.services.notifications import create_notification

    cutoff = datetime.now(UTC) - timedelta(hours=24)
    async with AsyncSessionLocal() as db:
        # Lectura cross-tenant intencionada (el scheduler es global). Cada
        # notificación lleva su tenant_id explícito.
        set_current_tenant(None)
        res = await db.execute(
            select(WorkflowExecution)
            .options(selectinload(WorkflowExecution.workflow))
            .where(
                WorkflowExecution.status == "failed",
                WorkflowExecution.notified.is_(False),
                WorkflowExecution.started_at >= cutoff,
            )
        )
        execs = res.scalars().all()
        notified = 0
        for ex in execs:
            payload = ex.trigger_payload or {}
            # Desatendida = disparada por el sistema (scheduler/catchup/evento),
            # no por el usuario desde la UI (manual → trigger_payload sin source).
            is_unattended = isinstance(payload, dict) and bool(payload.get("source"))
            if is_unattended:
                wf_name = ex.workflow.name if ex.workflow else "Automatización"
                reason = (ex.result_log or "Error desconocido").strip()[:300]
                await create_notification(
                    db,
                    tenant_id=ex.tenant_id,
                    title=f"La automatización «{wf_name}» falló",
                    body=reason,
                    kind="error",
                    payload={
                        "execution_id": str(ex.id),
                        "workflow_id": str(ex.workflow_id),
                    },
                )
                notified += 1
            ex.notified = True
        set_current_tenant(None)
        await db.commit()
        if notified:
            logger.warning(
                "[ALERTS] %d ejecución(es) de workflow fallidas notificadas al gestor.",
                notified,
            )
        return {"notified": notified}


async def emit_month_end_events():
    """Día 1 de cada mes: emite el evento `month_end` para cada tenant activo.

    El payload lleva el mes RECIÉN CERRADO (no el actual). Las rutinas de
    cierre mensual (asientos borrador, resumen, etc.) escuchan este evento.
    Idempotente por tenant+mes vía IdempotencyGuard.
    """
    try:
        await _emit_month_end_events()
    except Exception as e:
        logger.error("[SCHEDULER] Error en emit_month_end_events: %s", e)


async def _emit_month_end_events():
    from app.db.models.auth import Tenant
    from app.services import events_catalog as ev
    from app.services.event_bus import emit_event

    today = datetime.now(zoneinfo.ZoneInfo("Europe/Madrid")).date()
    closed = (today.replace(day=1) - timedelta(days=1))  # último día del mes cerrado
    period = f"{closed.year}-{closed.month:02d}"
    guard = IdempotencyGuard()

    async with AsyncSessionLocal() as db:
        # Lectura cross-tenant intencionada (el scheduler es global).
        set_current_tenant(None)
        res = await db.execute(select(Tenant.id).where(Tenant.is_active.is_(True)))
        tenant_ids = [row[0] for row in res.all()]

    emitted = 0
    for tid in tenant_ids:
        key = f"{tid}:{period}"
        if await guard.already_executed("month_end", key):
            continue
        set_current_tenant(str(tid))
        async with AsyncSessionLocal() as db:
            await emit_event(
                db, tid, None, ev.MONTH_END,
                {"month": closed.month, "year": closed.year, "period": period},
            )
        await guard.mark_executed("month_end", key, {"period": period})
        emitted += 1
    set_current_tenant(None)
    if emitted:
        logger.info("[SCHEDULER] month_end %s emitido para %d tenant(s).", period, emitted)
    return {"emitted": emitted, "period": period}


async def send_scheduled_email_campaigns():
    """Cada minuto: envía las campañas de email `scheduled` cuyo
    `scheduled_at` ya venció. El envío real lo hace
    `services/email_marketing.send_campaign` (mismo código que el botón
    "enviar ahora"), que marca sending → sent y protege contra dobles envíos.
    """
    try:
        await _send_scheduled_email_campaigns()
    except Exception as e:
        logger.error("[EMAIL-MKT] Error en send_scheduled_email_campaigns: %s", e)


async def _send_scheduled_email_campaigns():
    from app.db.models.email_marketing import EmailCampaign
    from app.services.email_marketing import send_campaign

    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        # Lectura cross-tenant intencionada (el scheduler es global).
        set_current_tenant(None)
        res = await db.execute(
            select(EmailCampaign.id, EmailCampaign.tenant_id).where(
                EmailCampaign.status == "scheduled",
                EmailCampaign.scheduled_at.isnot(None),
                EmailCampaign.scheduled_at <= now,
            )
        )
        due = res.all()

    sent = 0
    for campaign_id, tenant_id in due:
        set_current_tenant(str(tenant_id))
        await send_campaign(str(campaign_id), str(tenant_id))
        sent += 1
    set_current_tenant(None)
    if sent:
        logger.info("[EMAIL-MKT] %d campaña(s) programada(s) enviada(s).", sent)
    return {"sent": sent}
