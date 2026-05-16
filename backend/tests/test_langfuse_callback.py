"""Tests del helper get_langfuse_callback().

Cubre los 3 caminos:
- Keys vacías → None (caso default)
- Keys configuradas pero paquete no instalado → None (degradación)
- Keys + paquete instalados → handler real (con import opcional)
"""

import importlib.util

import pytest
from app.core import llm_callbacks

_langfuse_available = (
    importlib.util.find_spec("langfuse") is not None
    and importlib.util.find_spec("langchain") is not None
)


def test_returns_none_when_keys_empty(monkeypatch):
    monkeypatch.setattr(llm_callbacks.settings, "LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setattr(llm_callbacks.settings, "LANGFUSE_SECRET_KEY", "")
    assert llm_callbacks.get_langfuse_callback("tenant-A") is None


def test_returns_none_when_only_one_key(monkeypatch):
    """Ambas keys son obligatorias; con una sola, no se activa."""
    monkeypatch.setattr(llm_callbacks.settings, "LANGFUSE_PUBLIC_KEY", "pk_test")
    monkeypatch.setattr(llm_callbacks.settings, "LANGFUSE_SECRET_KEY", "")
    assert llm_callbacks.get_langfuse_callback("tenant-A") is None


def test_returns_none_when_package_missing(monkeypatch):
    """Si las keys están pero el import falla, degrada silenciosamente."""
    monkeypatch.setattr(llm_callbacks.settings, "LANGFUSE_PUBLIC_KEY", "pk_test")
    monkeypatch.setattr(llm_callbacks.settings, "LANGFUSE_SECRET_KEY", "sk_test")

    # Force ImportError simulando paquete ausente.
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("langfuse"):
            raise ImportError("simulated absence")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert llm_callbacks.get_langfuse_callback("tenant-A") is None


@pytest.mark.skipif(
    not _langfuse_available, reason="langfuse no instalado en el venv local"
)
def test_returns_handler_when_keys_and_package_present(monkeypatch):
    monkeypatch.setattr(llm_callbacks.settings, "LANGFUSE_PUBLIC_KEY", "pk_test")
    monkeypatch.setattr(llm_callbacks.settings, "LANGFUSE_SECRET_KEY", "sk_test")
    monkeypatch.setattr(llm_callbacks.settings, "LANGFUSE_HOST", "https://example.com")

    handler = llm_callbacks.get_langfuse_callback(
        tenant_id="t1", agent="billing", task_id="task-xyz"
    )
    assert handler is not None
    # No assert sobre la API interna del CallbackHandler — solo que se devolvió uno.
