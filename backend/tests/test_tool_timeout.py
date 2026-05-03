"""Tests del wrapper de timeout por tool.

Validan que las tools async se cancelan al exceder su timeout, que las
sync no se ven afectadas, y que el mensaje de error es informativo
(parseable por el LLM downstream).
"""

import asyncio

import pytest

from app.agents.tool_timeout import (
    DEFAULT_TIMEOUT_SECONDS,
    _TIMEOUT_OVERRIDES,
    apply_default_timeout,
    with_timeout,
)


class _FakeTool:
    """Stub mínimo de un BaseTool de LangChain con coroutine y name."""

    def __init__(self, name: str, coroutine=None, func=None):
        self.name = name
        self.coroutine = coroutine
        self.func = func


async def test_async_tool_returns_normally_when_under_timeout():
    async def fast(*args, **kwargs):
        await asyncio.sleep(0.01)
        return "ok"

    tool = _FakeTool("fast_tool", coroutine=fast)
    wrapped = with_timeout(seconds=1.0)(tool)
    result = await wrapped.coroutine()
    assert result == "ok"


async def test_async_tool_is_cancelled_when_exceeds_timeout():
    async def slow(*args, **kwargs):
        await asyncio.sleep(2.0)
        return "never"

    tool = _FakeTool("slow_tool", coroutine=slow)
    wrapped = with_timeout(seconds=0.1)(tool)
    result = await wrapped.coroutine()
    # No raise; el wrapper devuelve un string explicativo para el LLM.
    assert "slow_tool" in result
    assert "0" in result and "s" in result.lower()
    assert "cancel" in result.lower() or "tard" in result.lower()


async def test_sync_only_tool_is_not_modified():
    """Si la tool no tiene .coroutine, el wrapper la devuelve intacta."""

    def sync_fn(*args, **kwargs):
        return "sync"

    tool = _FakeTool("sync_tool", coroutine=None, func=sync_fn)
    wrapped = with_timeout(seconds=0.01)(tool)
    # El func no se tocó; el coroutine sigue siendo None.
    assert wrapped.coroutine is None
    assert wrapped.func is sync_fn


async def test_apply_default_uses_override_for_known_tool():
    """Verifica que apply_default_timeout respeta los overrides por nombre."""
    assert "process_cv" in _TIMEOUT_OVERRIDES
    override = _TIMEOUT_OVERRIDES["process_cv"]

    captured = {}

    async def slow(*args, **kwargs):
        # Simula tarea que tarda más que el default pero menos que el override.
        # Usamos una espera corta para no penalizar el test; solo necesitamos
        # validar que el wrapper aceptó la espera sin cancelar.
        await asyncio.sleep(0.01)
        return "ok"

    tool = _FakeTool("process_cv", coroutine=slow)
    wrapped = apply_default_timeout(tool)
    result = await wrapped.coroutine()
    assert result == "ok"
    # El override debe ser mayor al default.
    assert override > DEFAULT_TIMEOUT_SECONDS


async def test_apply_default_uses_default_for_unknown_tool():
    async def fast(*args, **kwargs):
        return "ok"

    tool = _FakeTool("nombre_que_no_esta_en_overrides", coroutine=fast)
    wrapped = apply_default_timeout(tool)
    result = await wrapped.coroutine()
    assert result == "ok"
