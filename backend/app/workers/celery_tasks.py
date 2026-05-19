"""
Celery task wrappers for the orchestrator.

Each wrapper runs the async orchestrator inside asyncio.run(), which is safe
with Celery's default prefork pool (each worker is its own OS process with no
pre-existing event loop). Do NOT use with gevent/eventlet pools.
"""
from __future__ import annotations

import asyncio
import logging

from app.celery_app import celery_app

_log = logging.getLogger(__name__)

if celery_app is not None:

    @celery_app.task(
        name="execute_orchestrator",
        bind=True,
        max_retries=3,
        default_retry_delay=10,
        acks_late=True,
    )
    def celery_execute_orchestrator(self, task_id: str, tenant_id: str | None = None) -> None:
        """Run execute_orchestrator(task_id) inside a fresh event loop.

        Fase 3 (RLS): `tenant_id` se propaga desde el dispatcher para que el
        worker fije el ContextVar ANTES de la query de bootstrap.
        """
        from app.workers.tasks_orchestrator import execute_orchestrator

        try:
            asyncio.run(execute_orchestrator(task_id, tenant_id))
        except Exception as exc:
            _log.exception("celery_execute_orchestrator falló para task_id=%s", task_id)
            raise self.retry(exc=exc)

    @celery_app.task(
        name="resume_orchestrator",
        bind=True,
        max_retries=2,
        default_retry_delay=5,
        acks_late=True,
    )
    def celery_resume_orchestrator(self, task_id: str, tenant_id: str | None = None) -> None:
        """Run resume_orchestrator(task_id) inside a fresh event loop.

        Fase 3 (RLS): `tenant_id` opcional para propagación temprana del contexto.
        """
        from app.workers.tasks_orchestrator import resume_orchestrator

        try:
            asyncio.run(resume_orchestrator(task_id, tenant_id))
        except Exception as exc:
            _log.exception("celery_resume_orchestrator falló para task_id=%s", task_id)
            raise self.retry(exc=exc)

else:
    # Stubs so import never fails regardless of Redis availability
    celery_execute_orchestrator = None  # type: ignore[assignment]
    celery_resume_orchestrator = None   # type: ignore[assignment]
