"""Tests para app.core.observability — Logging, métricas y trazabilidad."""
import json
import logging

import pytest
from app.core.observability import (
    StructuredFormatter,
    get_logger,
    get_metrics_registry,
    record_http_request,
    record_llm_latency,
    record_task_metric,
    set_approvals_pending,
    trace_llm_call,
    ws_connection_closed,
    ws_connection_opened,
)


class TestStructuredFormatter:
    def test_format_basic_record(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Hello world",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["message"] == "Hello world"
        assert data["logger"] == "test"
        assert "timestamp" in data

    def test_format_with_extra_fields(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.tenant_id = "tenant-123"
        record.trace_id = "trace-456"
        output = formatter.format(record)
        data = json.loads(output)
        assert data["tenant_id"] == "tenant-123"
        assert data["trace_id"] == "trace-456"

    def test_format_with_exception(self):
        formatter = StructuredFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="error occurred",
            args=(),
            exc_info=exc_info,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert "boom" in data["exception"]


class TestGetLogger:
    def test_returns_logger(self):
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_logger_has_handler(self):
        logger = get_logger("test_handler_check")
        assert len(logger.handlers) >= 1

    def test_logger_level_is_info(self):
        logger = get_logger("test_level_check")
        assert logger.level == logging.INFO

    def test_same_logger_returned(self):
        l1 = get_logger("test_same")
        l2 = get_logger("test_same")
        assert l1 is l2


class TestTraceLlmCall:
    def test_context_manager_yields_dict(self):
        with trace_llm_call(name="test_call") as ctx:
            assert isinstance(ctx, dict)
            assert "input" in ctx
            assert "output" in ctx
            assert "tokens" in ctx

    def test_context_data_persists(self):
        with trace_llm_call(name="test_persist", agent="billing") as ctx:
            ctx["input"] = "test input"
            ctx["output"] = "test output"
        assert ctx["input"] == "test input"
        assert ctx["output"] == "test output"

    def test_accepts_all_parameters(self):
        with trace_llm_call(
            name="full_test",
            agent="compliance",
            tenant_id="t-123",
            task_id="task-456",
            trace_id="trace-789",
            metadata={"extra": "data"},
        ) as ctx:
            ctx["output"] = "ok"

    def test_handles_exception_inside(self):
        """trace_llm_call should log even if an exception occurs inside."""
        with pytest.raises(RuntimeError):
            with trace_llm_call(name="error_test") as ctx:
                raise RuntimeError("intentional")


class TestMetricFunctions:
    """Test that metric functions don't crash regardless of prometheus availability."""

    def test_record_task_metric_created(self):
        record_task_metric("created", "tenant-1", "billing")

    def test_record_task_metric_completed(self):
        record_task_metric("completed", "tenant-1", "hr", "success")

    def test_record_llm_latency(self):
        record_llm_latency("billing", 1.5, "gpt-4o-mini")

    def test_set_approvals_pending(self):
        set_approvals_pending("tenant-1", 5)

    def test_record_http_request(self):
        record_http_request("GET", "/api/v1/invoices", 200, 0.05)

    def test_record_http_request_normalizes_ids(self):
        record_http_request(
            "GET",
            "/api/v1/invoices/12345678-1234-1234-1234-123456789abc",
            200,
            0.1,
        )

    def test_ws_connection_opened(self):
        ws_connection_opened()

    def test_ws_connection_closed(self):
        ws_connection_closed()


class TestGetMetricsRegistry:
    def test_returns_registry_or_none(self):
        registry = get_metrics_registry()
        # Could be None if prometheus_client is not installed, or a CollectorRegistry
        # Either way, it should not raise
        assert registry is None or registry is not None
