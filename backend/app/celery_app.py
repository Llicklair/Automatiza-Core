"""
Celery application factory.

Only active when REDIS_URL is configured. When Redis is absent the module
exports ``celery_app = None`` and the system falls back to in-process
asyncio task execution (existing behaviour, zero regression).
"""
from __future__ import annotations

import logging

_log = logging.getLogger(__name__)


def _make_celery():
    from app.core.config import settings

    if not settings.REDIS_URL:
        return None

    try:
        from celery import Celery

        app = Celery(
            "automatizapyme",
            broker=settings.REDIS_URL,
            backend=settings.REDIS_URL,
            include=["app.workers.celery_tasks"],
        )
        app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="Europe/Madrid",
            enable_utc=True,
            task_acks_late=True,
            task_reject_on_worker_lost=True,
            worker_prefetch_multiplier=1,
            task_routes={
                "execute_orchestrator": {"queue": "orchestrator"},
                "resume_orchestrator": {"queue": "orchestrator"},
            },
        )
        _log.info("Celery configurado con broker: %s", settings.REDIS_URL)
        return app

    except ImportError:
        _log.warning("celery no instalado — usando ejecución en proceso")
        return None


celery_app = _make_celery()
