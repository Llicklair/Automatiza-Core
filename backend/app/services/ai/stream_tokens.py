"""Helper de streaming token-a-token desde LLM hacia TaskEventHub (UI.AGT v2).

Patrón: en lugar de `await llm.ainvoke(messages)` que devuelve la respuesta
completa, usar `await stream_llm(llm, messages, task_id=...)` que:

  1. Llama `llm.astream(messages)` (LangChain estándar).
  2. Por cada chunk con contenido, publica un evento al `TaskEventHub`
     con `type="token"` + `delta="<texto>"` + `task_id`.
  3. Acumula los chunks en una `AIMessage` equivalente al .ainvoke() y
     la devuelve al caller — drop-in replacement.

El frontend (UI.AGT) ya está suscrito al SSE del `task_id`, así que los
tokens fluyen al ChatSection en tiempo real.

Si la cancelación llega via `task_runner.cancel(task_id)`, el
`asyncio.CancelledError` se propaga limpiamente — el agente termina y
el frontend ve estado `cancelled`.

Diseñado como wrapper opt-in: cada agente decide cuándo usar este helper
en lugar de `.ainvoke()`. La adopción es gradual.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("services.ai.stream_tokens")

# Importamos el hub a nivel de módulo para que los tests puedan
# monkeypatch `stream_tokens.task_event_hub`. Si el import falla en
# entorno sin workflow, degradamos a None.
try:
    from app.services.workflow.task_event_hub import task_event_hub  # noqa: F401
except Exception:  # pragma: no cover
    task_event_hub = None  # type: ignore[assignment]


async def stream_llm(
    llm: Any,
    messages: list,
    *,
    task_id: str | None = None,
    agent_name: str = "unknown",
) -> Any:
    """Llama `llm.astream(messages)`, publica tokens al hub, devuelve mensaje acumulado.

    Si `task_id` es `None`, se comporta exactamente como `await llm.ainvoke(messages)`
    (no publica nada, no añade overhead de streaming) — útil para tests que
    no tienen un task asociado o para llamadas internas que no quieren UI.
    """
    # Sin task_id no hay UI consumiendo — degradar a ainvoke clásico.
    if task_id is None:
        return await llm.ainvoke(messages)

    accumulated_text: list[str] = []
    final_chunk: Any = None
    token_count = 0

    async for chunk in llm.astream(messages):
        # `chunk` es típicamente un `AIMessageChunk` de LangChain. Su atributo
        # `content` es string (o lista de partes en tool-calling). Sumamos
        # AIMessageChunks para obtener el AIMessage final.
        final_chunk = chunk if final_chunk is None else final_chunk + chunk

        content = getattr(chunk, "content", "")
        if isinstance(content, str) and content:
            accumulated_text.append(content)
            token_count += 1
            if task_event_hub is not None:
                try:
                    await task_event_hub.publish(task_id, {
                        "type": "token",
                        "task_id": task_id,
                        "agent": agent_name,
                        "delta": content,
                    })
                except Exception as e:  # pragma: no cover
                    logger.debug("publish token falló (silenciado): %s", e)

    logger.debug(
        "stream_llm task=%s agent=%s tokens_emitidos=%d",
        task_id, agent_name, token_count,
    )
    return final_chunk
