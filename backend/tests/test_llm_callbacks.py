"""Unit tests for UsageTrackingCallback and token extraction logic."""
from unittest.mock import MagicMock

import pytest
from app.core.llm_callbacks import UsageTrackingCallback, _extract_tokens
from app.services import llm_usage_tracker
from langchain_core.outputs import ChatGeneration, LLMResult

TENANT = "test-tenant-callback"


@pytest.fixture(autouse=True)
def clean():
    llm_usage_tracker.flush_tenant(TENANT)
    yield
    llm_usage_tracker.flush_tenant(TENANT)


# ── Provider detection ────────────────────────────────────────────────────────

def test_detects_anthropic_from_serialized():
    cb = UsageTrackingCallback(TENANT, "billing")
    cb.on_llm_start({"name": "ChatAnthropic"}, [])
    assert cb._current_provider == "anthropic"


def test_detects_openai_from_serialized():
    cb = UsageTrackingCallback(TENANT, "billing")
    cb.on_llm_start({"name": "ChatOpenAI"}, [])
    assert cb._current_provider == "openai"


def test_detects_groq_from_serialized():
    cb = UsageTrackingCallback(TENANT, "billing")
    cb.on_llm_start({"name": "ChatGroq"}, [])
    assert cb._current_provider == "groq"


def test_detects_via_id_list():
    cb = UsageTrackingCallback(TENANT, "billing")
    cb.on_llm_start({"id": ["langchain", "chat_models", "ChatAnthropic"]}, [])
    assert cb._current_provider == "anthropic"


# ── Token extraction ──────────────────────────────────────────────────────────

def _make_result_with_token_usage(prompt_tokens: int, completion_tokens: int) -> LLMResult:
    return LLMResult(
        generations=[[]],
        llm_output={"token_usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }},
    )


def _make_result_with_usage_metadata(input_tokens: int, output_tokens: int) -> LLMResult:
    msg = MagicMock()
    msg.usage_metadata = {"input_tokens": input_tokens, "output_tokens": output_tokens}
    gen = MagicMock(spec=ChatGeneration)
    gen.message = msg
    return LLMResult(generations=[[gen]], llm_output={})


def _make_result_with_anthropic_usage(input_tokens: int, output_tokens: int) -> LLMResult:
    return LLMResult(
        generations=[[]],
        llm_output={"usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }},
    )


def test_extract_tokens_from_token_usage():
    result = _make_result_with_token_usage(100, 50)
    tin, tout = _extract_tokens(result)
    assert tin == 100
    assert tout == 50


def test_extract_tokens_from_usage_metadata():
    result = _make_result_with_usage_metadata(200, 80)
    tin, tout = _extract_tokens(result)
    assert tin == 200
    assert tout == 80


def test_extract_tokens_from_anthropic_usage():
    result = _make_result_with_anthropic_usage(300, 120)
    tin, tout = _extract_tokens(result)
    assert tin == 300
    assert tout == 120


def test_extract_tokens_returns_zero_on_empty():
    result = LLMResult(generations=[[]], llm_output={})
    tin, tout = _extract_tokens(result)
    assert tin == 0
    assert tout == 0


# ── on_llm_end records usage ──────────────────────────────────────────────────

def test_on_llm_end_records_to_tracker():
    cb = UsageTrackingCallback(TENANT, "billing")
    cb._current_provider = "anthropic"
    cb.on_llm_end(_make_result_with_token_usage(100, 50))

    stats = llm_usage_tracker.get_monthly_stats(TENANT, months=1)
    assert stats[0]["total_calls"] == 1
    assert stats[0]["total_tokens_in"] == 100


def test_on_llm_end_does_not_record_zero_tokens():
    cb = UsageTrackingCallback(TENANT, "billing")
    cb._current_provider = "anthropic"
    cb.on_llm_end(LLMResult(generations=[[]], llm_output={}))

    stats = llm_usage_tracker.get_monthly_stats(TENANT, months=1)
    assert stats == []


def test_on_llm_end_survives_exceptions():
    cb = UsageTrackingCallback(TENANT, "billing")
    cb._current_provider = "anthropic"
    # Pass a broken result — should not raise
    cb.on_llm_end(MagicMock(side_effect=Exception("boom")))
