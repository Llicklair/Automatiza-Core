"""Tests del TaskEventHub (UI.AGT — streaming SSE de progreso de tareas)."""
import asyncio

import pytest
from app.services.workflow.task_event_hub import TaskEventHub


@pytest.mark.asyncio
class TestTaskEventHub:
    async def test_subscribe_recibe_eventos(self):
        hub = TaskEventHub()
        queue = await hub.subscribe("task-1")

        await hub.publish("task-1", {"step": 1, "summary": "ok"})
        event = await asyncio.wait_for(queue.get(), timeout=0.5)

        assert event["step"] == 1
        assert event["summary"] == "ok"

    async def test_publish_a_task_id_distinto_no_propaga(self):
        hub = TaskEventHub()
        queue_a = await hub.subscribe("task-a")
        await hub.subscribe("task-b")

        await hub.publish("task-b", {"step": 1})

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue_a.get(), timeout=0.1)

    async def test_dos_suscriptores_misma_task_reciben_ambos(self):
        hub = TaskEventHub()
        q1 = await hub.subscribe("task-1")
        q2 = await hub.subscribe("task-1")

        await hub.publish("task-1", {"v": "hola"})

        e1 = await asyncio.wait_for(q1.get(), timeout=0.5)
        e2 = await asyncio.wait_for(q2.get(), timeout=0.5)
        assert e1["v"] == "hola"
        assert e2["v"] == "hola"

    async def test_unsubscribe_limpia(self):
        hub = TaskEventHub()
        queue = await hub.subscribe("task-1")
        hub.unsubscribe("task-1", queue)
        assert "task-1" not in hub._subscribers

    async def test_signal_end_cierra_stream(self):
        hub = TaskEventHub()
        events = []

        async def consumer():
            async for event in hub.stream("task-1", timeout_seconds=2.0):
                events.append(event)

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)  # esperar a que subscribe

        await hub.publish("task-1", {"step": 1})
        await hub.publish("task-1", {"step": 2})
        await hub.signal_end("task-1")

        await asyncio.wait_for(task, timeout=1.0)
        assert len(events) == 2
        assert events[0]["step"] == 1
        assert events[1]["step"] == 2

    async def test_stream_se_limpia_al_terminar(self):
        hub = TaskEventHub()

        async def consumer():
            async for _ in hub.stream("task-1", timeout_seconds=2.0):
                pass

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)
        await hub.signal_end("task-1")
        await asyncio.wait_for(task, timeout=1.0)

        assert "task-1" not in hub._subscribers

    async def test_publish_sin_suscriptores_no_falla(self):
        hub = TaskEventHub()
        # No raises ni efectos colaterales.
        await hub.publish("nadie-escucha", {"step": 1})
