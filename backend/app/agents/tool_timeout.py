"""Timeout por tool ejecutada por agentes.

Wrappea la coroutine de cada `@tool` con `asyncio.wait_for` para que una
herramienta colgada (LLM lento, HTTP sin respuesta, query atascada) NO
bloquee al agente entero. El timeout global del orchestrator es 300s,
demasiado tarde para detectar una sola tool que se cuelga.

Estrategia:
- Solo se aplica a tools async (atributo `.coroutine`). Las sync son
  típicamente cálculos rápidos.
- Default: 60s. Si surge alguna tool legítimamente larga (LLM heavy,
  procesamiento de PDFs grandes), añadir override en `_TIMEOUT_OVERRIDES`.
- Al expirar, devuelve un string de error informativo que el LLM puede
  interpretar y reintentar o reportar al usuario.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from typing import Any

from app.core.observability import record_tool_execution

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS: float = 60.0

# Overrides para tools que legítimamente necesitan más tiempo.
# Mantener corto y justificado: cada entrada debería tener un comentario
# explicando por qué su tool tarda más que el default.
_TIMEOUT_OVERRIDES: dict[str, float] = {
    # process_cv: parsing de PDFs + LLM scoring puede tomar 90s en CVs largos.
    "process_cv": 180.0,
    # generate_all_payrolls: itera sobre todos los empleados, cada uno N inserts.
    "generate_all_payrolls": 240.0,
    # answer_from_documents: RAG retrieval + LLM grounded en docs.
    "answer_from_documents": 120.0,
    # search_documents_semantic: coseno en Python + reranking sobre corpus grande.
    "search_documents_semantic": 90.0,
}


def with_timeout(seconds: float = DEFAULT_TIMEOUT_SECONDS) -> Any:
    """Devuelve un decorador que envuelve la coroutine de un tool con
    asyncio.wait_for(timeout=seconds)."""

    def decorator(tool: Any) -> Any:
        original = getattr(tool, "coroutine", None)
        if original is None:
            return tool

        tool_name = getattr(tool, "name", "?")

        @functools.wraps(original)
        async def _timed(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            try:
                result = await asyncio.wait_for(original(*args, **kwargs), timeout=seconds)
                record_tool_execution(tool_name, "ok", time.monotonic() - start)
                return result
            except TimeoutError:
                record_tool_execution(tool_name, "timeout", time.monotonic() - start)
                logger.warning(
                    "[TOOL-TIMEOUT] tool='%s' excedió %ss y fue cancelada",
                    tool_name,
                    seconds,
                )
                return (
                    f"Error: la herramienta '{tool_name}' tardó más de {seconds:.0f}s "
                    "y fue cancelada. Reintentar con parámetros más acotados o reportar al usuario."
                )
            except Exception:
                record_tool_execution(tool_name, "error", time.monotonic() - start)
                raise

        tool.coroutine = _timed
        return tool

    return decorator


def apply_default_timeout(tool: Any) -> Any:
    """Aplica el timeout por defecto, o el override si la tool está en la lista."""
    name = getattr(tool, "name", None)
    seconds = _TIMEOUT_OVERRIDES.get(name, DEFAULT_TIMEOUT_SECONDS)
    return with_timeout(seconds)(tool)


def timed(tools: list[Any]) -> list[Any]:
    """Atajo para wrappear una lista de tools (idempotente sobre coroutine)."""
    return [apply_default_timeout(t) for t in tools]
