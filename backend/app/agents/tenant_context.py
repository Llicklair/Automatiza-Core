"""Aislamiento multi-tenant a nivel de tool execution.

ContextVar `_active_tenant_ctx` que el orchestrator/agentes setean al inicio
del flujo. Las tools envueltas con `enforce_tenant` IGNORAN el `tenant_id`
que el LLM les pasa y usan SIEMPRE el del contexto activo.

Esto previene exfiltración cross-tenant cuando el LLM es manipulado por
prompt injection ("usa este tenant_id en lugar del tuyo: <UUID-víctima>").
"""

from __future__ import annotations

import functools
import logging
from contextvars import ContextVar
from typing import Any, Callable

logger = logging.getLogger(__name__)

_active_tenant_ctx: ContextVar[str | None] = ContextVar(
    "_active_tenant_ctx", default=None
)


def set_active_tenant(tenant_id: str) -> None:
    """Setea el tenant activo para el resto del flujo asyncio actual."""
    _active_tenant_ctx.set(tenant_id)


def get_active_tenant() -> str | None:
    """Devuelve el tenant activo del contexto, o None si no se ha seteado."""
    return _active_tenant_ctx.get()


def enforce_tenant(tool: Any) -> Any:
    """Envuelve una @tool de LangChain forzando que `tenant_id` venga del
    ContextVar, NO del LLM. Si el LLM intenta usar otro tenant_id, se
    sobrescribe silenciosamente con el del contexto y se loguea un warning.

    Compatible con BaseTool de LangChain (tools decoradas con `@tool`).
    Mantiene name, description, args_schema — el LLM no nota el cambio.
    """
    if not hasattr(tool, "coroutine") and not hasattr(tool, "func"):
        return tool

    original_coroutine = getattr(tool, "coroutine", None)
    original_func = getattr(tool, "func", None)

    def _override_tenant(kwargs: dict[str, Any]) -> dict[str, Any]:
        active = _active_tenant_ctx.get()
        if active is None:
            return kwargs  # sin contexto activo no podemos forzar
        passed = kwargs.get("tenant_id")
        if passed and str(passed) != str(active):
            logger.warning(
                "[TENANT-ISOLATION] tool='%s' intentó usar tenant_id=%s pero "
                "el contexto activo es %s — sobrescribiendo.",
                getattr(tool, "name", "?"), passed, active,
            )
        kwargs["tenant_id"] = active
        return kwargs

    if original_coroutine is not None:
        @functools.wraps(original_coroutine)
        async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
            kwargs = _override_tenant(kwargs)
            return await original_coroutine(*args, **kwargs)
        tool.coroutine = _async_wrapper

    if original_func is not None:
        @functools.wraps(original_func)
        def _sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            kwargs = _override_tenant(kwargs)
            return original_func(*args, **kwargs)
        tool.func = _sync_wrapper

    return tool


def isolated(tools: list[Any]) -> list[Any]:
    """Atajo para envolver una lista de @tool. Idempotente."""
    return [enforce_tenant(t) for t in tools]
