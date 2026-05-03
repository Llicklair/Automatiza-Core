"""Request context — ContextVar para el request_id de la petición HTTP actual.

El middleware `RequestLoggerMiddleware` lo setea al recibir cada request HTTP.
Se lee desde:
  - `StructuredFormatter`: auto-inyecta `request_id` en cada log JSON sin
    necesidad de pasarlo explícitamente como `extra={"request_id": ...}`.
  - `trace_llm_call`: lo usa como `trace_id` por defecto si no se pasa
    explícito, agrupando todas las llamadas LLM de un mismo request en una
    única traza Langfuse.
  - Workers Celery / agentes LangGraph: pueden propagarlo manualmente
    cuando se invocan desde una request HTTP.

asyncio garantiza que cada Task hereda copia del contexto al crearse, por
lo que requests concurrentes no se mezclan sus request_ids.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

_current_request_id_ctx: ContextVar[str | None] = ContextVar(
    "current_request_id", default=None
)


def set_current_request_id(request_id: str | None) -> None:
    """Setea el request_id activo para el resto del contexto async actual."""
    _current_request_id_ctx.set(request_id)


def get_current_request_id() -> str | None:
    """Devuelve el request_id activo o None si no se ha seteado."""
    return _current_request_id_ctx.get()


@contextmanager
def request_context(request_id: str) -> Iterator[None]:
    """Context manager para scoping explícito (workers, jobs programados
    que provienen de una request HTTP y quieren correlacionar logs)."""
    token = _current_request_id_ctx.set(request_id)
    try:
        yield
    finally:
        _current_request_id_ctx.reset(token)
