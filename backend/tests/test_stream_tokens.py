"""Tests del helper de streaming token-a-token (UI.AGT v2)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.stream_tokens import stream_llm
from app.services.workflow.task_event_hub import TaskEventHub


class FakeChunk:
    """Mock minimal de AIMessageChunk de LangChain (soporta +=)."""

    def __init__(self, content: str):
        self.content = content

    def __add__(self, other: "FakeChunk") -> "FakeChunk":
        return FakeChunk(self.content + (other.content or ""))


class FakeLLM:
    """LLM mock que astream-ea chunks predefinidos."""

    def __init__(self, chunks: list[str]):
        self._chunks = chunks

    async def astream(self, _messages):
        for c in self._chunks:
            yield FakeChunk(c)

    async def ainvoke(self, _messages):
        return FakeChunk("".join(self._chunks))


@pytest.mark.asyncio
class TestStreamLLM:
    async def test_sin_task_id_se_comporta_como_ainvoke(self):
        llm = FakeLLM(["hola", " mundo"])
        result = await stream_llm(llm, [{"role": "user", "content": "x"}])
        assert result.content == "hola mundo"

    async def test_con_task_id_publica_tokens_al_hub(self, monkeypatch):
        # Sustituimos la singleton del hub por una nueva instancia para aislar.
        hub = TaskEventHub()
        monkeypatch.setattr(
            "app.services.ai.stream_tokens.task_event_hub", hub, raising=False,
        )

        async def patched_import():
            return hub

        # Suscriptor que recoge eventos.
        queue = await hub.subscribe("t-1")

        llm = FakeLLM(["hola", " ", "mundo"])
        # Re-importamos stream_llm con el monkeypatch ya aplicado.
        from app.services.ai import stream_tokens
        monkeypatch.setattr(stream_tokens, "task_event_hub", hub, raising=False)

        # Llamamos a la función (con el hub patcheado).
        await stream_tokens.stream_llm(
            llm, [{"role": "user", "content": "x"}],
            task_id="t-1", agent_name="billing",
        )

        # Verifica que recibimos 3 eventos `type=token` con los deltas.
        events = []
        for _ in range(3):
            ev = await asyncio.wait_for(queue.get(), timeout=0.5)
            events.append(ev)

        assert len(events) == 3
        assert events[0]["type"] == "token"
        assert events[0]["delta"] == "hola"
        assert events[0]["agent"] == "billing"
        assert events[0]["task_id"] == "t-1"
        assert events[2]["delta"] == "mundo"

    async def test_acumula_mensaje_final_correctamente(self, monkeypatch):
        from app.services.ai import stream_tokens
        hub = TaskEventHub()
        monkeypatch.setattr(stream_tokens, "task_event_hub", hub, raising=False)

        llm = FakeLLM(["uno ", "dos ", "tres"])
        result = await stream_tokens.stream_llm(
            llm, [], task_id="t-2", agent_name="x",
        )

        assert result.content == "uno dos tres"

    async def test_chunks_vacios_no_emiten_eventos(self, monkeypatch):
        from app.services.ai import stream_tokens
        hub = TaskEventHub()
        monkeypatch.setattr(stream_tokens, "task_event_hub", hub, raising=False)
        queue = await hub.subscribe("t-3")

        # Chunks vacíos intercalados con contenido real.
        llm = FakeLLM(["", "hola", "", " ", "mundo", ""])
        await stream_tokens.stream_llm(
            llm, [], task_id="t-3", agent_name="x",
        )

        # Deben emitirse solo 3 eventos (los chunks no vacíos).
        events = []
        try:
            while True:
                ev = await asyncio.wait_for(queue.get(), timeout=0.1)
                events.append(ev)
        except asyncio.TimeoutError:
            pass

        assert len(events) == 3
        assert [e["delta"] for e in events] == ["hola", " ", "mundo"]

    async def test_hub_caido_no_rompe_streaming(self, monkeypatch):
        """Si el hub falla al publicar, el LLM debe seguir streameando."""
        from app.services.ai import stream_tokens

        class FailingHub:
            async def publish(self, *_a, **_kw):
                raise RuntimeError("hub down")

        monkeypatch.setattr(stream_tokens, "task_event_hub", FailingHub(), raising=False)

        llm = FakeLLM(["a", "b", "c"])
        result = await stream_tokens.stream_llm(
            llm, [], task_id="t-4", agent_name="x",
        )

        # El stream concluyó y devolvió mensaje correcto a pesar del hub roto.
        assert result.content == "abc"
