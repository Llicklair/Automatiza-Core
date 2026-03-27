"""
APScheduler — tareas periódicas.

Arranca/para con el lifespan de FastAPI.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Europe/Madrid")


def register_jobs() -> None:
    """Registra las tareas periódicas (equivalente a beat_schedule)."""
    from app.workers.tasks_scheduler import (
        check_scheduled_workflows,
        process_recurring_invoices,
        cleanup_stuck_executions,
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

    # Cada 10 minutos: limpiar ejecuciones bloqueadas
    scheduler.add_job(
        cleanup_stuck_executions,
        IntervalTrigger(minutes=10),
        id="cleanup_stuck_executions",
        replace_existing=True,
        max_instances=1,
    )

    logger.info("Scheduler: %d tareas periódicas registradas", len(scheduler.get_jobs()))


async def start_scheduler() -> None:
    try:
        register_jobs()
        scheduler.start()
        logger.info("Scheduler arrancado")
        # Catch-up: ejecutar workflows perdidos mientras la app estaba cerrada
        from app.workers.tasks_scheduler import catchup_missed_workflows
        await catchup_missed_workflows()
    except Exception as e:
        logger.error("Error arrancando scheduler (no es fatal): %s", e)


async def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("Scheduler parado")
