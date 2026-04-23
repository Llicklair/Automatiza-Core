"""Tests para app.core.llm_factory — Fábrica centralizada de LLMs."""
import pytest

from app.core.llm.mock import MockChatModel
from app.core.llm_factory import (
    _tenant_llm_ctx,
    get_llm,
    get_llm_with_fallback,
    set_tenant_llm_context,
)


class TestGetLlm:
    def test_returns_mock_in_testing_without_keys(self):
        """In testing env with no API keys, get_llm returns MockChatModel."""
        llm = get_llm()
        assert isinstance(llm, MockChatModel)

    def test_explicit_mock_provider(self):
        llm = get_llm(provider="mock")
        assert isinstance(llm, MockChatModel)

    def test_unknown_provider_returns_mock(self):
        llm = get_llm(provider="nonexistent_provider_xyz")
        assert isinstance(llm, MockChatModel)

    def test_temperature_parameter_accepted(self):
        llm = get_llm(temperature=0.7)
        assert isinstance(llm, MockChatModel)

    def test_groq_without_key_returns_mock(self):
        llm = get_llm(provider="groq")
        assert isinstance(llm, MockChatModel)

    def test_gemini_without_key_returns_mock(self):
        llm = get_llm(provider="gemini")
        assert isinstance(llm, MockChatModel)

    def test_anthropic_without_key_returns_mock(self):
        llm = get_llm(provider="anthropic")
        assert isinstance(llm, MockChatModel)

    def test_openai_without_key_returns_mock(self):
        llm = get_llm(provider="openai")
        assert isinstance(llm, MockChatModel)

    def test_openrouter_without_key_returns_mock(self):
        llm = get_llm(provider="openrouter")
        assert isinstance(llm, MockChatModel)


class TestGetLlmWithFallback:
    def test_delegates_to_get_llm(self):
        llm = get_llm_with_fallback()
        assert isinstance(llm, MockChatModel)

    def test_accepts_temperature(self):
        llm = get_llm_with_fallback(temperature=0.5)
        assert isinstance(llm, MockChatModel)


class TestTenantLlmContext:
    def test_set_and_get_context(self):
        mock = MockChatModel()
        set_tenant_llm_context(mock)
        try:
            result = get_llm()
            assert result is mock
        finally:
            # Clean up context var
            _tenant_llm_ctx.set(None)

    def test_explicit_provider_ignores_context(self):
        mock = MockChatModel()
        set_tenant_llm_context(mock)
        try:
            result = get_llm(provider="mock")
            # With explicit provider, a new MockChatModel is created, not the ctx one
            assert isinstance(result, MockChatModel)
        finally:
            _tenant_llm_ctx.set(None)

    def test_context_default_is_none(self):
        _tenant_llm_ctx.set(None)
        result = get_llm()
        assert isinstance(result, MockChatModel)
