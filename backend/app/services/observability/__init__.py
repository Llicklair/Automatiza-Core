"""Observabilidad: trazas, métricas, logs estructurados."""

from app.services.observability.agent_trace import record_agent_execution

__all__ = ["record_agent_execution"]
