"""Pub/sub in-process por `task_id` para SSE streaming (UI.AGT).

Reutiliza la infraestructura existente: cada vez que el orquestador hace
`ws_manager.broadcast_to_tenant({..., "task_id": ...})`, este hub recibe
una copia del evento y lo distribuye a cualquier suscriptor SSE que
esté escuchando esa task concreta.

Ventajas frente a un endpoint que escuche la BD por polling:
- 0 latencia (in-memory asyncio.Queue por suscriptor)
- 0 carga de BD extra
- Aprovecha el fanout de eventos ya implementado en `_dispatch_handlers`

Limitaciones MVP:
- In-process only. Si el deployment escala a múltiples uvicorn workers,
  hay que migrar a Redis pub/sub (un canal por task_id). Por ahora
  AutomatizaPyme corre en un único proceso desktop (Electron + uvicorn
  embebido).
- Sin persistencia: si un cliente se conecta tarde, no recibe los eventos
  emitidos antes. Para reconstruir histórico, leer `Task.agent_results`.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

logger = logging.getLogger("task_event_hub")

# Sentinel value usado para señalizar fin-de-stream a los suscriptores.
_END_OF_STREAM: dict[str, Any] = {"__eos__": True}


class TaskEventHub:
    """Pub/sub in-process indexado por `task_id`."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)

    async def subscribe(self, task_id: str) -> asyncio.Queue[dict[str, Any]]:
        """Registra un suscriptor para `task_id` y devuelve su cola."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        self._subscribers[task_id].append(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Quita un suscriptor; limpia la lista si queda vacía."""
        if task_id in self._subscribers:
            try:
                self._subscribers[task_id].remove(queue)
            except ValueError:
                pass
            if not self._subscribers[task_id]:
                self._subscribers.pop(task_id, None)

    async def publish(self, task_id: str, event: dict[str, Any]) -> None:
        """Envía `event` a todos los suscriptores activos de `task_id`.

        No bloquea si una cola está llena — descarta el evento para ese
        suscriptor lento. Es la decisión consensuada: preferimos perder
        algún token de progreso antes que ralentizar al agente.
        """
        queues = self._subscribers.get(task_id, [])
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("task_event_hub queue full task=%s — drop", task_id)

    async def signal_end(self, task_id: str) -> None:
        """Notifica a todos los suscriptores que el stream terminó."""
        await self.publish(task_id, _END_OF_STREAM)

    async def stream(self, task_id: str, timeout_seconds: float = 600.0) -> AsyncIterator[dict[str, Any]]:
        """Async iterator: yieldea eventos hasta EOS o timeout.

        Diseñado para usar desde el handler SSE: `async for event in hub.stream(...)`.
        El timeout de 10 min es defensa contra conexiones zombi.
        """
        queue = await self.subscribe(task_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=timeout_seconds)
                except TimeoutError:
                    logger.info("task_event_hub stream timeout task=%s", task_id)
                    return
                if event.get("__eos__"):
                    return
                yield event
        finally:
            self.unsubscribe(task_id, queue)


# Singleton global
task_event_hub = TaskEventHub()
