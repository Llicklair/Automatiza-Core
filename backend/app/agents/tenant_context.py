"""Aislamiento multi-tenant a nivel de tool execution.

Las tools envueltas con `enforce_tenant` IGNORAN el `tenant_id` que el LLM
les pasa y usan SIEMPRE el del contexto activo. Esto previene exfiltración
cross-tenant cuando el LLM es manipulado por prompt injection
("usa este tenant_id en lugar del tuyo: <UUID-víctima>").

El ContextVar es el mismo que setea el middleware FastAPI: vive en
`app.core.tenant_context`. Aquí se re-exporta con su nombre histórico para
mantener compatibilidad con los callers existentes en agents/orchestrator.
"""

from __future__ import annotations

import functools
import logging
from typing import Any

from app.core.tenant_context import (
    _current_tenant_ctx as _active_tenant_ctx,
    get_current_tenant,
    set_current_tenant,
)

logger = logging.getLogger(__name__)


def set_active_tenant(tenant_id: str) -> None:
    """Alias retro-compat de set_current_tenant."""
    set_current_tenant(tenant_id)


def get_active_tenant() -> str | None:
    """Alias retro-compat de get_current_tenant."""
    return get_current_tenant()


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
