"""Tests del ContextVar central de tenant en `app.core.tenant_context`.

Cubre los invariantes que la Fase 3 (RLS) va a asumir:
- get/set/clear básicos.
- require_current_tenant() lanza si no hay contexto.
- tenant_context() restaura el valor anterior al salir.
- asyncio.gather con tenants distintos NO contamina los contextos entre tasks.
- El alias en app.agents.tenant_context comparte el mismo ContextVar.
"""

import asyncio

import pytest
from app.core.tenant_context import (
    get_current_tenant,
    require_current_tenant,
    set_current_tenant,
    tenant_context,
)

T_A = "11111111-1111-1111-1111-111111111111"
T_B = "22222222-2222-2222-2222-222222222222"


@pytest.fixture(autouse=True)
def _reset_context():
    """Limpia el ContextVar al inicio y al final de cada test."""
    set_current_tenant(None)
    yield
    set_current_tenant(None)


def test_set_get_roundtrip():
    assert get_current_tenant() is None
    set_current_tenant(T_A)
    assert get_current_tenant() == T_A
    set_current_tenant(None)
    assert get_current_tenant() is None


def test_require_raises_when_unset():
    assert get_current_tenant() is None
    with pytest.raises(RuntimeError, match="No tenant in current context"):
        require_current_tenant()


def test_require_returns_when_set():
    set_current_tenant(T_A)
    assert require_current_tenant() == T_A


def test_tenant_context_restores_previous():
    set_current_tenant(T_A)
    with tenant_context(T_B):
        assert get_current_tenant() == T_B
    assert get_current_tenant() == T_A


def test_tenant_context_restores_on_exception():
    set_current_tenant(T_A)
    with pytest.raises(ValueError):
        with tenant_context(T_B):
            assert get_current_tenant() == T_B
            raise ValueError("boom")
    assert get_current_tenant() == T_A


@pytest.mark.asyncio
async def test_concurrent_tasks_do_not_contaminate():
    """Dos coroutines en asyncio.gather con tenants distintos deben mantener
    contextos independientes — éste es el caso real de dos requests HTTP
    simultáneos al mismo proceso uvicorn."""

    observed: dict[str, str] = {}

    async def worker(name: str, tid: str) -> None:
        set_current_tenant(tid)
        # Cede control varias veces para forzar interleaving.
        for _ in range(5):
            await asyncio.sleep(0)
            assert get_current_tenant() == tid, (
                f"{name} esperaba {tid} pero observó {get_current_tenant()}"
            )
        observed[name] = get_current_tenant()

    await asyncio.gather(worker("A", T_A), worker("B", T_B))
    assert observed == {"A": T_A, "B": T_B}


@pytest.mark.asyncio
async def test_outer_context_isolated_from_gathered_tasks():
    """El ContextVar seteado dentro de una task de gather NO debe afectar
    al contexto del caller después de que la task termine."""
    set_current_tenant(T_A)

    async def child() -> None:
        set_current_tenant(T_B)

    await asyncio.gather(child())
    assert get_current_tenant() == T_A


def test_alias_in_agents_module_shares_same_contextvar():
    """app.agents.tenant_context se consolidó para apuntar al mismo ContextVar
    que app.core.tenant_context. Si esto se rompe en el futuro, los tools
    decoradas con enforce_tenant usarían un contexto distinto al del request."""
    from app.agents.tenant_context import (
        get_active_tenant,
        set_active_tenant,
    )

    set_current_tenant(T_A)
    assert get_active_tenant() == T_A

    set_active_tenant(T_B)
    assert get_current_tenant() == T_B
