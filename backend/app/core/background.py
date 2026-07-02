# Copyright © 2026 Marcos Recio <marcosreciosanchez@gmail.com> — AutomatizaCore
# SPDX-License-Identifier: LicenseRef-Proprietary
"""Lanzar coroutines en segundo plano sin que el GC las recolecte a medio correr.

`asyncio.create_task` NO guarda una referencia fuerte a la task: si el llamador no
la retiene, el recolector de basura puede destruirla antes de que termine (RUF006).
`spawn` mantiene viva la referencia hasta que la task acaba y la libera sola via
done-callback. De paso, loguea las excepciones no recuperadas que de otro modo se
perderían en silencio (la task era fire-and-forget y nadie hacía await).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)

# Referencias fuertes a las tasks en vuelo. Cada una se quita sola al completarse.
_background_tasks: set[asyncio.Task[Any]] = set()


def spawn(coro: Coroutine[Any, Any, Any], *, name: str | None = None) -> asyncio.Task[Any]:
    """Crea una task fire-and-forget reteniendo su referencia (evita RUF006).

    Equivalente a `asyncio.create_task(coro)` pero sin el riesgo de que el GC la
    mate. Devuelve la task por si el llamador quiere cancelarla; ignorarla es seguro.
    """
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)
    task.add_done_callback(_on_task_done)
    return task


def _on_task_done(task: asyncio.Task[Any]) -> None:
    _background_tasks.discard(task)
    if not task.cancelled() and task.exception() is not None:
        logger.error("Task de fondo %r terminó con excepción", task.get_name(), exc_info=task.exception())
