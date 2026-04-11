"""
In-process async task runner.

Mantiene un registro de tareas en vuelo para poder cancelarlas.
"""

import asyncio
import logging
from typing import Any, Coroutine

logger = logging.getLogger(__name__)


class TaskRunner:
    """Ejecutor de tareas async en background dentro del proceso uvicorn."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}

    async def submit(
        self,
        name: str,
        coro: Coroutine[Any, Any, Any],
        task_id: str,
    ) -> None:
        """Lanza una corrutina como tarea de fondo, indexada por task_id."""
        if task_id in self._tasks and not self._tasks[task_id].done():
            logger.warning("Tarea %s ya en ejecución, ignorando duplicado", task_id)
            return

        async def _wrapper():
            try:
                await coro
            except asyncio.CancelledError:
                logger.info("Tarea %s cancelada", task_id)
            except Exception as exc:
                logger.exception("Error en tarea %s (%s)", task_id, name)
                # Safety net: marcar tarea como failed si sigue en executing
                try:
                    from app.workers.tasks_orchestrator import _mark_task_failed

                    await _mark_task_failed(task_id, f"{type(exc).__name__}: {exc}")
                except Exception:
                    logger.error("No se pudo marcar tarea %s como failed", task_id)
            finally:
                self._tasks.pop(task_id, None)

        task = asyncio.create_task(_wrapper(), name=f"{name}:{task_id}")
        self._tasks[task_id] = task
        logger.info("Tarea %s (%s) lanzada", task_id, name)

    async def submit_delayed(
        self,
        name: str,
        coro: Coroutine[Any, Any, Any],
        task_id: str,
        delay_seconds: float,
    ) -> None:
        """Lanza una corrutina tras un retardo."""

        async def _delayed():
            await asyncio.sleep(delay_seconds)
            await coro

        await self.submit(name, _delayed(), task_id)

    def cancel(self, task_id: str) -> bool:
        """Cancela una tarea en vuelo. Devuelve True si se canceló."""
        task = self._tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            logger.info("Tarea %s cancelada por solicitud", task_id)
            return True
        return False

    def is_running(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        return task is not None and not task.done()

    @property
    def active_count(self) -> int:
        return sum(1 for t in self._tasks.values() if not t.done())

    async def shutdown(self) -> None:
        """Cancela todas las tareas pendientes (para cierre limpio)."""
        for tid in list(self._tasks):
            self.cancel(tid)
        # Esperar a que terminen (máx 10s)
        tasks = [t for t in self._tasks.values() if not t.done()]
        if tasks:
            await asyncio.wait(tasks, timeout=10)
        logger.info("TaskRunner cerrado (%d tareas canceladas)", len(tasks))


# Singleton global
task_runner = TaskRunner()
