"""Orchestrator (Coordinador) package — superficie pública mínima.

Estructura interna:
  state.py          — Tipos: TaskStatus, SubTask, AgentResult, OrchestratorState, VALID_DOMAINS
  classifier.py     — Clasificación de intenciones (LLM + keywords)
  node_handlers.py  — Funciones de nodo del grafo (init, plan, validate, dispatch, summarize)
  utils.py          — _format_summary, _extract_month_year
  helpers.py        — _lock/unlock_document, _save_ai_result_as_document/csv
  dispatchers/      — Un módulo por agente (billing, hr, crm, etc.)
  _core.py          — Routing + construcción del grafo LangGraph + build_orchestrator
  _plan_handlers.py — Plan execution + health-check para AIEmployees custom
  _dispatch_handlers.py — Invocación de agentes builtin y dinámicos

Solo se re-exportan los símbolos consumidos desde fuera del paquete. Los
detalles internos (nodos del grafo, dispatchers, helpers) se importan
directamente desde sus submódulos cuando hace falta.

Public surface (verificado con grep contra app/ + tests/):
  - orchestrator       (workers/tasks_orchestrator.py)
  - OrchestratorState  (workers/tasks_orchestrator.py)
  - TaskStatus         (services/ai/node_graph_helpers.py, workers/*)
"""

from app.agents.orchestrator._core import orchestrator
from app.agents.orchestrator.state import OrchestratorState, TaskStatus

__all__ = [
    "orchestrator",
    "OrchestratorState",
    "TaskStatus",
]
