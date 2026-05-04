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
_deferred_task: "asyncio.Task[None] | None" = None


def register_jobs() -> None:
    """Registra las tareas periódicas (equivalente a beat_schedule)."""
    from app.workers.tasks_scheduler import (
        check_scheduled_workflows,
        cleanup_stuck_executions,
        process_recurring_invoices,
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

    # Diario a las 8:30 (Europe/Madrid): alertas automáticas de negocio
    from app.services.alerts import run_daily_alerts

    scheduler.add_job(
        run_daily_alerts,
        CronTrigger(hour=8, minute=30),
        id="daily_alerts",
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
