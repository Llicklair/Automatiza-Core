"""
APScheduler — tareas periódicas.

Arranca/para con el lifespan de FastAPI.
"""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Europe/Madrid")
_deferred_task: asyncio.Task[None] | None = None


def register_jobs() -> None:
    """Registra las tareas periódicas (equivalente a beat_schedule)."""
    from app.workers.tasks_scheduler import (
        check_failed_workflow_executions,
        check_scheduled_workflows,
        cleanup_stuck_executions,
        emit_month_end_events,
        process_recurring_invoices,
        publish_scheduled_posts,
    )

    # Cada minuto: comprobar workflows programados
    scheduler.add_job(
        check_scheduled_workflows,
        CronTrigger(minute="*"),
        id="check_scheduled_workflows",
        replace_existing=True,
        max_instances=1,
    )

    # Diario a las 8:00 (Europe/Madrid): facturas recurrentes
    scheduler.add_job(
        process_recurring_invoices,
        CronTrigger(hour=8, minute=0),
        id="process_recurring_invoices",
        replace_existing=True,
        max_instances=1,
    )

    # Cada 5 minutos: publicar posts de marketing programados
    scheduler.add_job(
        publish_scheduled_posts,
        IntervalTrigger(minutes=5),
        id="publish_scheduled_posts",
        replace_existing=True,
        max_instances=1,
    )

    # Día 1 de cada mes a las 7:00: evento month_end (mes recién cerrado) por tenant
    scheduler.add_job(
        emit_month_end_events,
        CronTrigger(day=1, hour=7, minute=0),
        id="emit_month_end_events",
        replace_existing=True,
        max_instances=1,
    )

    # Cada 10 minutos: limpiar ejecuciones bloqueadas
    scheduler.add_job(
        cleanup_stuck_executions,
        IntervalTrigger(minutes=10),
        id="cleanup_stuck_executions",
        replace_existing=True,
        max_instances=1,
    )

    # Cada 10 minutos: volcar el consumo LLM en memoria a la DB (snapshot) para
    # que el dashboard sobreviva a una caída entre apagados gráciles.
    from app.services.llm_usage_tracker import persist_to_db as _persist_llm_usage

    scheduler.add_job(
        _persist_llm_usage,
        IntervalTrigger(minutes=10),
        id="persist_llm_usage",
        replace_existing=True,
        max_instances=1,
    )

    # Cada 10 minutos: notificar al gestor las automatizaciones desatendidas que
    # fallaron (no deben fallar en silencio).
    scheduler.add_job(
        check_failed_workflow_executions,
        IntervalTrigger(minutes=10),
        id="check_failed_workflow_executions",
        replace_existing=True,
        max_instances=1,
    )

    # Diario a las 8:30 (Europe/Madrid): alertas automáticas de negocio
    from app.services.alerts import run_daily_alerts

    scheduler.add_job(
        run_daily_alerts,
        CronTrigger(hour=8, minute=30),
        id="daily_alerts",
        replace_existing=True,
        max_instances=1,
    )

    # Diario a las 8:45 (Europe/Madrid): reposición automática — genera pedidos
    # de compra borrador para productos bajo su punto de pedido (idempotente).
    from app.services.inventory.reorder_service import run_auto_reorder

    scheduler.add_job(
        run_auto_reorder,
        CronTrigger(hour=8, minute=45),
        id="daily_auto_reorder",
        replace_existing=True,
        max_instances=1,
    )

    # Diario a las 4:00 (Europe/Madrid): backup pg_dump + rotación.
    # Hora baja para no competir con la actividad del usuario.
    from app.services.backup import run_backup_job

    scheduler.add_job(
        run_backup_job,
        CronTrigger(hour=4, minute=0),
        id="daily_backup",
        replace_existing=True,
        max_instances=1,
    )

    # Diario a las 8:15: detección de tenants pendientes de backfill Verifactu (A.5).
    # No ejecuta el backfill — solo emite warning auditable porque la nif_emisor
    # debe confirmarla un humano admin.
    from app.workers.backfill_alerts import check_pending_verifactu_backfills

    scheduler.add_job(
        check_pending_verifactu_backfills,
        CronTrigger(hour=8, minute=15),
        id="verifactu_backfill_check",
        replace_existing=True,
        max_instances=1,
    )

    logger.info("Scheduler: %d tareas periódicas registradas", len(scheduler.get_jobs()))


async def start_scheduler() -> None:
    try:
        register_jobs()
        scheduler.start()
        logger.info("Scheduler arrancado")
    except Exception as e:
        logger.error("Error arrancando scheduler (no es fatal): %s", e)

    # Catch-up y heartbeats se lanzan como tareas de fondo para no bloquear
    # el lifespan de FastAPI (uvicorn no sirve HTTP hasta que lifespan termine).
    async def _deferred_startup():
        try:
            from app.workers.tasks_scheduler import catchup_missed_workflows

            await catchup_missed_workflows()
        except Exception as e:
            logger.error("Error en catchup_missed_workflows (no es fatal): %s", e)
        try:
            from app.services.integration.heartbeat import bootstrap_employee_heartbeats

            await bootstrap_employee_heartbeats()
        except Exception as e:
            logger.error("Bootstrap heartbeats falló (no es fatal): %s", e)

    global _deferred_task
    _deferred_task = asyncio.create_task(_deferred_startup())


async def stop_scheduler() -> None:
    global _deferred_task
    if _deferred_task and not _deferred_task.done():
        _deferred_task.cancel()
        _deferred_task = None
    scheduler.shutdown(wait=False)
    logger.info("Scheduler parado")
