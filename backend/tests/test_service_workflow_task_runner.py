"""Tests para app.services.workflow.task_runner.TaskRunner.

Cubre el ejecutor in-process de tareas asíncronas. Cada workflow/task
pasa por aquí en deployments single-process (desktop Electron + uvicorn
embebido). Sin cobertura, cualquier bug se traduce en tareas colgadas o
duplicadas en producción.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from app.services.workflow.task_runner import TaskRunner


@pytest.fixture
async def runner():
    r = TaskRunner()
    yield r
    await r.shutdown()


@pytest.mark.asyncio
class TestTaskRunner:
    async def test_submit_lanza_task_y_registra(self, runner):
        done = asyncio.Event()

        async def work():
            done.set()

        await runner.submit("test", work(), "tid-1")
        # Esperar a que la tarea termine
        for _ in range(20):
            if done.is_set():
                break
            await asyncio.sleep(0.01)
        assert done.is_set()
        # Tras terminar, se autoelimina del registro
        for _ in range(20):
            if not runner.is_running("tid-1"):
                break
            await asyncio.sleep(0.01)
        assert not runner.is_running("tid-1")

    async def test_duplicado_se_ignora(self, runner):
        gate = asyncio.Event()
        started = asyncio.Event()
        counter = {"n": 0}

        async def work():
            counter["n"] += 1
            started.set()
            await gate.wait()

        await runner.submit("test", work(), "tid-dup")
        # Esperar a que la primera arranque
        await started.wait()
        # Segundo submit con mismo task_id mientras corre → ignorado
        # (la coro pasada se cierra para evitar RuntimeWarning)
        await runner.submit("test", work(), "tid-dup")

        assert counter["n"] == 1  # solo el primero arrancó
        gate.set()
        await asyncio.sleep(0.05)

    async def test_cancel_detiene_tarea(self, runner):
        cancelled = asyncio.Event()

        async def work():
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                cancelled.set()
                raise

        await runner.submit("test", work(), "tid-cancel")
        # Pequeña espera para que arranque
        await asyncio.sleep(0.02)
        result = runner.cancel("tid-cancel")
        assert result is True
        await asyncio.sleep(0.05)
        assert cancelled.is_set()

    async def test_cancel_de_inexistente_devuelve_false(self, runner):
        assert runner.cancel("no-existe") is False

    async def test_cancel_de_task_ya_terminada_devuelve_false(self, runner):
        async def work():
            pass

        await runner.submit("test", work(), "tid-done")
        await asyncio.sleep(0.05)
        # Ya terminó → cancel devuelve False
        assert runner.cancel("tid-done") is False

    async def test_is_running_y_active_count(self, runner):
        gate = asyncio.Event()

        async def work():
            await gate.wait()

        assert runner.active_count == 0
        await runner.submit("t", work(), "tid-r1")
        await runner.submit("t", work(), "tid-r2")
        await asyncio.sleep(0.02)
        assert runner.is_running("tid-r1")
        assert runner.is_running("tid-r2")
        assert runner.active_count == 2
        gate.set()
        await asyncio.sleep(0.05)
        assert runner.active_count == 0

    async def test_submit_delayed_respeta_retardo(self, runner):
        started_at = asyncio.get_event_loop().time()
        done_at = {"t": None}

        async def work():
            done_at["t"] = asyncio.get_event_loop().time()

        await runner.submit_delayed("t", work(), "tid-delayed", delay_seconds=0.1)
        # Esperar a que ejecute
        for _ in range(30):
            if done_at["t"] is not None:
                break
            await asyncio.sleep(0.02)
        assert done_at["t"] is not None
        elapsed = done_at["t"] - started_at
        # Tolerancia razonable: al menos 0.08s
        assert elapsed >= 0.08

    async def test_exception_en_tarea_dispara_mark_failed(self, runner):
        with patch(
            "app.workers.tasks_orchestrator._mark_task_failed",
            new=AsyncMock(),
        ) as mock_mark:

            async def work():
                raise RuntimeError("boom")

            await runner.submit("t", work(), "tid-err")
            # Esperar a que el wrapper la procese
            await asyncio.sleep(0.1)

        mock_mark.assert_awaited_once()
        args = mock_mark.await_args.args
        assert args[0] == "tid-err"
        assert "boom" in args[1]
        assert "RuntimeError" in args[1]
        # Y el registro se limpió
        assert not runner.is_running("tid-err")

    async def test_exception_en_mark_failed_no_crashea(self, runner):
        """Si _mark_task_failed también falla, el wrapper no debe colgar."""
        with patch(
            "app.workers.tasks_orchestrator._mark_task_failed",
            new=AsyncMock(side_effect=RuntimeError("mark broken")),
        ):

            async def work():
                raise RuntimeError("original")

            await runner.submit("t", work(), "tid-double-err")
            await asyncio.sleep(0.05)
            # No debe haber excepción pendiente que rompa runner
            assert not runner.is_running("tid-double-err")

    async def test_shutdown_cancela_pendientes(self):
        r = TaskRunner()
        gate = asyncio.Event()

        async def work():
            try:
                await gate.wait()
            except asyncio.CancelledError:
                raise

        await r.submit("t", work(), "tid-s1")
        await r.submit("t", work(), "tid-s2")
        await asyncio.sleep(0.02)
        assert r.active_count == 2

        await r.shutdown()
        # Tras shutdown, ninguna tarea pendiente
        await asyncio.sleep(0.05)
        assert r.active_count == 0
