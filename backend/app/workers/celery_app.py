"""
Worker Celery para ejecución asíncrona del orquestador.
Los workers se ejecutan en procesos separados y consumen tareas de Redis.
"""
import asyncio

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "pyme_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Madrid",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,  # Un mensaje a la vez por worker
    result_expires=3600,  # Resultados expiran en 1h para evitar memory leak en Redis
    # ── Celery Beat: tareas periódicas ─────────────────────────────────────────
    beat_schedule={
        "check-scheduled-workflows": {
            "task": "check_scheduled_workflows",
            "schedule": crontab(minute="*"),  # Cada minuto
        },
        "process-recurring-invoices": {
            "task": "process_recurring_invoices",
            "schedule": crontab(hour="8", minute="0"),  # Cada día a las 8:00
        },
        "cleanup-stuck-executions": {
            "task": "cleanup_stuck_executions",
            "schedule": crontab(minute="*/10"),  # Cada 10 minutos
        },
    },
)



def run_async(coro):
    """Helper para ejecutar coroutines async desde Celery (sync)."""
    from app.db.base import engine

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.run_until_complete(engine.dispose())
        loop.close()
        asyncio.set_event_loop(None)


# ── Importar módulos de tareas para que Celery las descubra ──────────────────
from app.workers.tasks_orchestrator import run_orchestrator, resume_orchestrator  # noqa: E402, F401
from app.workers.tasks_node_engine import run_node_engine, resume_node_engine  # noqa: E402, F401
from app.workers.tasks_scheduler import (  # noqa: E402, F401
    check_scheduled_workflows,
    process_recurring_invoices,
    cleanup_stuck_executions,
)
