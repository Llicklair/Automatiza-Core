"""Unit tests for make_cached_system_message and _resolve_active_provider."""
from unittest.mock import MagicMock

import pytest
from app.core.llm_factory import (
    _resolve_active_provider,
    _tenant_llm_ctx,
    make_cached_system_message,
    set_tenant_llm_context,
)
from langchain_core.messages import SystemMessage


@pytest.fixture(autouse=True)
def reset_ctx():
    """Reset ContextVar between tests."""
    token = _tenant_llm_ctx.set(None)
    yield
    _tenant_llm_ctx.reset(token)


# ── _resolve_active_provider ──────────────────────────────────────────────────

def test_resolve_returns_anthropic_for_anthropic_module():
    mock_llm = MagicMock()
    type(mock_llm).__module__ = "langchain_anthropic.chat_models"
    set_tenant_llm_context(mock_llm)
    assert _resolve_active_provider() == "anthropic"


def test_resolve_returns_other_for_openai_module():
    mock_llm = MagicMock()
    type(mock_llm).__module__ = "langchain_openai.chat_models"
    set_tenant_llm_context(mock_llm)
    assert _resolve_active_provider() == "other"


def test_resolve_returns_other_for_groq_module():
    mock_llm = MagicMock()
    type(mock_llm).__module__ = "langchain_groq.chat_models"
    set_tenant_llm_context(mock_llm)
    assert _resolve_active_provider() == "other"


def test_resolve_falls_back_to_settings_when_no_ctx(monkeypatch):
    from app.core import llm_factory
    monkeypatch.setattr(llm_factory.settings, "DEFAULT_LLM_PROVIDER", "openai")
    assert _resolve_active_provider() == "openai"


def test_resolve_falls_back_to_settings_anthropic(monkeypatch):
    from app.core import llm_factory
    monkeypatch.setattr(llm_factory.settings, "DEFAULT_LLM_PROVIDER", "anthropic")
    assert _resolve_active_provider() == "anthropic"


# ── make_cached_system_message ────────────────────────────────────────────────

def test_cached_message_with_anthropic_provider():
    mock_llm = MagicMock()
    type(mock_llm).__module__ = "langchain_anthropic.chat_models"
    set_tenant_llm_context(mock_llm)

    msg = make_cached_system_message("You are a helpful assistant.")

    assert isinstance(msg, SystemMessage)
    assert isinstance(msg.content, list)
    assert len(msg.content) == 1
    block = msg.content[0]
    assert block["type"] == "text"
    assert block["text"] == "You are a helpful assistant."
    assert block["cache_control"] == {"type": "ephemeral"}


def test_cached_message_with_openai_provider():
    mock_llm = MagicMock()
    type(mock_llm).__module__ = "langchain_openai.chat_models"
    set_tenant_llm_context(mock_llm)

    msg = make_cached_system_message("You are a helpful assistant.")

    assert isinstance(msg, SystemMessage)
    assert isinstance(msg.content, str)
    assert msg.content == "You are a helpful assistant."


def test_cached_message_no_ctx_openai_default(monkeypatch):
    from app.core import llm_factory
    monkeypatch.setattr(llm_factory.settings, "DEFAULT_LLM_PROVIDER", "openai")

    msg = make_cached_system_message("hello")

    assert isinstance(msg.content, str)
    assert "cache_control" not in str(msg.content)


def test_cached_message_no_ctx_anthropic_default(monkeypatch):
    from app.core import llm_factory
    monkeypatch.setattr(llm_factory.settings, "DEFAULT_LLM_PROVIDER", "anthropic")

    msg = make_cached_system_message("hello")

    assert isinstance(msg.content, list)
    assert msg.content[0]["cache_control"] == {"type": "ephemeral"}


def test_cached_message_preserves_full_text():
    mock_llm = MagicMock()
    type(mock_llm).__module__ = "langchain_anthropic.chat_models"
    set_tenant_llm_context(mock_llm)

    long_text = "Line 1\nLine 2\nLine 3\n" * 100
    msg = make_cached_system_message(long_text)

    assert msg.content[0]["text"] == long_text
