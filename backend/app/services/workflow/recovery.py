"""
Startup recovery — limpia zombies dejados por reinicios del backend.

Cuando el proceso muere mientras hay tasks `executing`, el TaskRunner que
las poseía desaparece y no puede sincronizarlas. Lo mismo ocurre con
WorkflowExecutions `pending`/`running` cuyas tasks ya no existen
(p.ej. tras una limpieza de BD que borra `tasks` pero deja `workflow_executions`).

Esta función se llama una sola vez al arrancar, ANTES de aceptar tráfico.
Marca:
  - Tasks `executing` con `started_at` antiguo → `failed` (zombie).
  - WorkflowExecutions `pending`/`running` con task inexistente → `cancelled`.
  - WorkflowExecutions `pending`/`running` cuya task quedó `failed` por esta
    misma recovery → `failed` (sincroniza el estado).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.datetime_utils import as_aware
from app.db.base import AsyncSessionLocal
from app.db.models.models import Task, WorkflowExecution

logger = logging.getLogger(__name__)

# Margen tras el cual una task `executing` se considera zombie.
# Cualquier task viva supera este umbral solo en flujos extremos
# (LLMs lentos, PDFs grandes). 30 minutos es conservador.
_ZOMBIE_AFTER = timedelta(minutes=30)

# Umbral más agresivo cuando la task no produjo NINGÚN progreso
# (plan=None y agent_results vacíos): si no llegó ni al planner en
# 5 min, su worker está muerto seguro.
_NO_PROGRESS_ZOMBIE_AFTER = timedelta(minutes=5)


async def recover_stale_executions() -> dict[str, int]:
    """Marca zombies de tasks/workflow_executions al arrancar el backend."""
    now = datetime.now(UTC)
    zombie_cutoff = now - _ZOMBIE_AFTER
    no_progress_cutoff = now - _NO_PROGRESS_ZOMBIE_AFTER

    stats = {"tasks_failed": 0, "execs_cancelled": 0, "execs_failed": 0}

    try:
        async with AsyncSessionLocal() as db:
            # 1. Tasks `executing` consideradas zombie. Dos criterios:
            #    (a) started_at < hace 30 min (umbral conservador general)
            #    (b) started_at < hace 5 min Y ningún progreso (plan=None y
            #        sin agent_results). Una task viva ya tendría plan en
            #        menos de 5 min, así que esto captura workers muertos
            #        antes incluso del planner.
            stale_tasks_r = await db.execute(
                select(Task).where(
                    Task.status == "executing",
                    Task.started_at < no_progress_cutoff,
                )
            )
            candidates = stale_tasks_r.scalars().all()
            stale_tasks = [
                t
                for t in candidates
                if (as_aware(t.started_at) or now) < zombie_cutoff
                or (t.plan is None and not (t.agent_results or []))
            ]
            for t in stale_tasks:
                t.status = "failed"
                t.error_message = (
                    t.error_message
                    or "Backend reiniciado mientras la task estaba en ejecución (recovery)."
                )
                t.completed_at = now
            stats["tasks_failed"] = len(stale_tasks)

            # 2. WorkflowExecutions pending/running cuya task no existe → cancelled
            #    Subquery: ids de tasks que existen.
            execs_r = await db.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.status.in_(("pending", "running"))
                )
            )
            execs = execs_r.scalars().all()

            existing_task_ids = set()
            if execs:
                task_ids = {e.task_id for e in execs if e.task_id is not None}
                if task_ids:
                    t_r = await db.execute(
                        select(Task.id).where(Task.id.in_(task_ids))
                    )
                    existing_task_ids = {row[0] for row in t_r.all()}

            for ex in execs:
                # Sin task vinculada o task borrada → cancelled
                if ex.task_id is None or ex.task_id not in existing_task_ids:
                    ex.status = "cancelled"
                    ex.completed_at = now
                    ex.result_log = (
                        ex.result_log
                        or "Task asociada no existe (recovery al arrancar)."
                    )
                    stats["execs_cancelled"] += 1
                    continue
                # Si la task quedó failed (por el bloque 1), sincronizar
                # buscando el objeto que ya tenemos en la sesión.
                linked_task = next((t for t in stale_tasks if t.id == ex.task_id), None)
                if linked_task is not None:
                    ex.status = "failed"
                    ex.completed_at = now
                    ex.result_log = linked_task.error_message
                    stats["execs_failed"] += 1

            await db.commit()
    except Exception:
        logger.exception("[RECOVERY] Error reconciliando estado al arrancar")
        return stats

    if any(stats.values()):
        logger.warning(
            "[RECOVERY] Limpieza al arrancar: %s tasks zombi → failed, "
            "%s executions huérfanas → cancelled, %s executions sincronizadas → failed",
            stats["tasks_failed"],
            stats["execs_cancelled"],
            stats["execs_failed"],
        )
    return stats
