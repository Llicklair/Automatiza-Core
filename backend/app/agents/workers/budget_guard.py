"""Backward-compatibility shim — implementacion en services/agent_budget.py.

El modulo se movio el 2026-05-16 a `app.services.agent_budget` porque es
budget management generico, no logica de agente. Este shim se mantiene
para no romper:

- `app.agents.orchestrator._dispatch_handlers` que importa via
  `app.agents.workers`.
- Tests que parchean `app.agents.workers.check_agent_budget`
  (test_planner_custom_agents.py).
"""
from app.services.agent_budget import (
    check_agent_budget,
    get_budget_status,
    record_token_usage,
)

__all__ = ["check_agent_budget", "get_budget_status", "record_token_usage"]
