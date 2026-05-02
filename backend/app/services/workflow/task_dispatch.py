"""
Dispatch de tareas.

Cuando REDIS_URL está configurado, las tareas se enolan en Celery (workers
separados con reintentos). En caso contrario se ejecutan en proceso con
asyncio (comportamiento original, sin regresión).
"""
import logging

from app.core.config import settings
from app.services.workflow.task_runner import task_runner

_log = logging.getLogger(__name__)


def _celery_available() -> bool:
    from app.celery_app import celery_app
    return celery_app is not None and bool(settings.REDIS_URL)


async def dispatch_orchestrator(task_id: str) -> None:
    if _celery_available():
        from app.workers.celery_tasks import celery_execute_orchestrator
        celery_execute_orchestrator.delay(task_id)
        _log.info("Tarea %s encolada en Celery (queue=orchestrator)", task_id)
    else:
        from app.workers.tasks_orchestrator import execute_orchestrator
        await task_runner.submit("run_orchestrator", execute_orchestrator(task_id), task_id)


async def dispatch_resume_orchestrator(task_id: str) -> None:
    if _celery_available():
        from app.workers.celery_tasks import celery_resume_orchestrator
        celery_resume_orchestrator.delay(task_id)
        _log.info("Reanudación %s encolada en Celery", task_id)
    else:
        from app.workers.tasks_orchestrator import resume_orchestrator
        await task_runner.submit(
            "resume_orchestrator", resume_orchestrator(task_id), f"resume:{task_id}"
        )


async def dispatch_node_engine(execution_id: str) -> None:
    from app.workers.tasks_node_engine import run_node_engine

    await task_runner.submit(
        "run_node_engine", run_node_engine(execution_id), f"node:{execution_id}"
    )


async def dispatch_resume_node_engine(
    execution_id: str,
    from_node_id: str,
    delay_seconds: float = 0,
) -> None:
    from app.workers.tasks_node_engine import resume_node_engine

    task_key = f"resume_node:{execution_id}:{from_node_id}"

    if delay_seconds > 0:
        await task_runner.submit_delayed(
            "resume_node_engine",
            resume_node_engine(execution_id, from_node_id),
            task_key,
            delay_seconds,
        )
    else:
        await task_runner.submit(
            "resume_node_engine",
            resume_node_engine(execution_id, from_node_id),
            task_key,
        )


async def cancel_task(task_id: str) -> bool:
    """Cancela una tarea en vuelo."""
    return task_runner.cancel(task_id)
