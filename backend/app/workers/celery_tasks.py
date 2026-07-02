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
    from celery import Task as _CeleryTask

    class _OrchestratorTask(_CeleryTask):
        """Base task con dead-letter: cuando se agotan los reintentos (o falla de
        forma terminal), marca la Task de dominio como `failed` en BD.

        Sin esto, al agotar los retries Celery marca su propia task como FAILURE
        pero la fila Task del usuario se queda en `running` para siempre → el
        usuario observa un spinner eterno. El `task_id` de dominio viaja en
        `args[0]` (o en el kwarg `task_id`).
        """

        def on_failure(self, exc, task_id, args, kwargs, einfo):  # noqa: ANN001
            domain_task_id = (args[0] if args else None) or kwargs.get("task_id")
            if not domain_task_id:
                return
            from app.workers._orchestrator_state import _mark_task_failed

            try:
                asyncio.run(_mark_task_failed(str(domain_task_id), str(exc)))
                _log.error(
                    "[DEAD-LETTER] Task de dominio %s marcada como failed tras agotar reintentos: %s",
                    domain_task_id,
                    exc,
                )
            except Exception:
                _log.exception(
                    "[DEAD-LETTER] No se pudo marcar la task de dominio %s como failed",
                    domain_task_id,
                )

    @celery_app.task(
        name="execute_orchestrator",
        base=_OrchestratorTask,
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
            raise self.retry(exc=exc) from exc

    @celery_app.task(
        name="resume_orchestrator",
        base=_OrchestratorTask,
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
            raise self.retry(exc=exc) from exc

else:
    # Stubs so import never fails regardless of Redis availability
    celery_execute_orchestrator = None  # type: ignore[assignment]
    celery_resume_orchestrator = None  # type: ignore[assignment]
