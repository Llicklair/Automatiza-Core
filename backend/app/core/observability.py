"""
Capa de observabilidad — Fase 3.

Integra:
  - Langfuse: trazabilidad de llamadas LLM (prompts, tokens, latencia, coste)
  - Prometheus: métricas de negocio y rendimiento de la API
  - Logging estructurado: JSON con nivel, timestamp, tenant_id, trace_id

USO:
  from app.core.observability import trace_llm_call, record_task_metric, get_logger

  logger = get_logger(__name__)
  with trace_llm_call(name="billing_extraction", user_id=..., trace_id=...):
      result = await llm.ainvoke(...)
"""

import json
import logging
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from app.core.config import settings

# ─── Logger estructurado ──────────────────────────────────────────────────────


class StructuredFormatter(logging.Formatter):
    """Formatea los logs como JSON para ingestión en Loki/ELK."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        # Añadir campos extra si existen (tenant_id, task_id, trace_id)
        for field in ("tenant_id", "task_id", "trace_id", "agent", "duration_ms"):
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger con formato JSON estructurado."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


# ─── Langfuse (trazabilidad LLM) ──────────────────────────────────────────────

_langfuse_client = None


def _get_langfuse():
    """Inicializa Langfuse de forma lazy. Si no está configurado, devuelve None."""
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client
    if not getattr(settings, "LANGFUSE_PUBLIC_KEY", None) or not getattr(
        settings, "LANGFUSE_SECRET_KEY", None
    ):
        return None
    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=getattr(settings, "LANGFUSE_PUBLIC_KEY", ""),
            secret_key=getattr(settings, "LANGFUSE_SECRET_KEY", ""),
            host=getattr(settings, "LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    except ImportError:
        pass  # Langfuse no instalado — modo silencioso
    return _langfuse_client


@contextmanager
def trace_llm_call(
    name: str,
    agent: str = "unknown",
    tenant_id: str | None = None,
    task_id: str | None = None,
    trace_id: str | None = None,
    metadata: dict | None = None,
) -> Generator[dict, None, None]:
    """
    Context manager para trazabilidad de llamadas LLM.
    Compatible con Langfuse si está configurado; sin-op si no.

    USO:
        with trace_llm_call("billing_extraction", agent="billing") as ctx:
            ctx["input"] = messages
            result = await llm.ainvoke(messages)
            ctx["output"] = result.content
    """
    logger = get_logger("llm_trace")
    ctx: dict = {"input": None, "output": None, "tokens": 0}
    start = time.monotonic()
    trace_id = trace_id or str(uuid.uuid4())

    langfuse = _get_langfuse()
    trace = span = None

    if langfuse:
        trace = langfuse.trace(
            name=name,
            id=trace_id,
            user_id=tenant_id or "unknown",
            metadata={
                "agent": agent,
                "task_id": task_id,
                "tenant_id": tenant_id,
                **(metadata or {}),
            },
        )
        span = trace.span(name=f"{agent}.{name}")

    try:
        yield ctx
    finally:
        duration_ms = round((time.monotonic() - start) * 1000)
        if span:
            span.end(
                input=ctx.get("input"),
                output=ctx.get("output"),
                metadata={"duration_ms": duration_ms},
            )
        logger.info(
            f"LLM call: {name}",
            extra={
                "trace_id": trace_id,
                "agent": agent,
                "task_id": task_id or "",
                "tenant_id": tenant_id or "",
                "duration_ms": duration_ms,
            },
        )


# ─── Prometheus metrics ───────────────────────────────────────────────────────

_metrics_enabled = False
_registry: Any = None

try:
    from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

    _registry = CollectorRegistry()

    TASKS_CREATED = Counter(
        "automatizapyme_tasks_created_total",
        "Total de tareas creadas",
        ["tenant_id", "domain"],
        registry=_registry,
    )
    TASKS_COMPLETED = Counter(
        "automatizapyme_tasks_completed_total",
        "Total de tareas completadas",
        ["tenant_id", "domain", "status"],
        registry=_registry,
    )
    LLM_LATENCY = Histogram(
        "automatizapyme_llm_duration_seconds",
        "Latencia de llamadas LLM",
        ["agent", "model"],
        registry=_registry,
        buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    )
    APPROVALS_PENDING = Gauge(
        "automatizapyme_approvals_pending",
        "Aprobaciones pendientes por tenant",
        ["tenant_id"],
        registry=_registry,
    )

    # ── HTTP metrics (integrated via RequestLoggerMiddleware) ──
    HTTP_REQUESTS_TOTAL = Counter(
        "automatizapyme_http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status_code"],
        registry=_registry,
    )
    HTTP_REQUEST_DURATION = Histogram(
        "automatizapyme_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "path"],
        registry=_registry,
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )
    ACTIVE_WEBSOCKET_CONNECTIONS = Gauge(
        "automatizapyme_active_websocket_connections",
        "Number of active WebSocket connections",
        registry=_registry,
    )

    _metrics_enabled = True
except ImportError:
    pass  # prometheus_client no instalado


def record_task_metric(event: str, tenant_id: str, domain: str, status: str = ""):
    """Registra métricas de negocio. No-op si Prometheus no está disponible."""
    if not _metrics_enabled:
        return
    try:
        if event == "created":
            TASKS_CREATED.labels(tenant_id=tenant_id, domain=domain).inc()
        elif event == "completed":
            TASKS_COMPLETED.labels(tenant_id=tenant_id, domain=domain, status=status).inc()
    except Exception:
        pass  # Nunca crashear por métricas


def record_llm_latency(agent: str, duration_seconds: float, model: str = "gpt-4o-mini"):
    """Registra la latencia de una llamada LLM."""
    if not _metrics_enabled:
        return
    try:
        LLM_LATENCY.labels(agent=agent, model=model).observe(duration_seconds)
    except Exception:
        pass


def set_approvals_pending(tenant_id: str, count: int):
    """Actualiza el gauge de aprobaciones pendientes."""
    if not _metrics_enabled:
        return
    try:
        APPROVALS_PENDING.labels(tenant_id=tenant_id).set(count)
    except Exception:
        pass


def record_http_request(method: str, path: str, status_code: int, duration_seconds: float):
    """Record HTTP request metrics. No-op if Prometheus is unavailable."""
    if not _metrics_enabled:
        return
    try:
        # Normalize path to avoid high-cardinality labels (strip IDs)
        import re

        normalized = re.sub(r"/[0-9a-f-]{8,}", "/{id}", path)
        HTTP_REQUESTS_TOTAL.labels(
            method=method, path=normalized, status_code=str(status_code)
        ).inc()
        HTTP_REQUEST_DURATION.labels(method=method, path=normalized).observe(duration_seconds)
    except Exception:
        pass


def ws_connection_opened():
    """Increment active WebSocket connections gauge."""
    if not _metrics_enabled:
        return
    try:
        ACTIVE_WEBSOCKET_CONNECTIONS.inc()
    except Exception:
        pass


def ws_connection_closed():
    """Decrement active WebSocket connections gauge."""
    if not _metrics_enabled:
        return
    try:
        ACTIVE_WEBSOCKET_CONNECTIONS.dec()
    except Exception:
        pass


def get_metrics_registry():
    """Devuelve el registry de Prometheus para exponerlo en /metrics."""
    return _registry
