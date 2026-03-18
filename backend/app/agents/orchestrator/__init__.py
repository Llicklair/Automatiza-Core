"""
Paquete del orquestador — mantiene compatibilidad con imports existentes.

Antes:  from app.agents.orchestrator import orchestrator, OrchestratorState, ...
Ahora:  misma sintaxis, funciona igual.

Estructura:
  orchestrator/
    state.py        — Tipos: TaskStatus, SubTask, AgentResult, OrchestratorState
    classifier.py   — Clasificación de intenciones (LLM + keywords)
    utils.py        — _format_summary, _extract_month_year
    helpers.py      — _lock/unlock_document, _save_ai_result_as_document/csv
    dispatchers/    — Un módulo por agente (billing, hr, crm, etc.)
    _core.py        — Nodos del grafo LangGraph + build_orchestrator
    __init__.py     — Re-exporta todo (este archivo)
"""
from app.agents.orchestrator.state import (
    AgentResult,
    MAX_ITERATIONS,
    OrchestratorState,
    SubTask,
    TaskStatus,
    VALID_DOMAINS,
)

from app.agents.orchestrator._core import (
    orchestrator,
    build_orchestrator,
    plan_node,
    validate_node,
    dispatch_node,
    load_knowledge_node,
    route_after_validate,
    route_after_dispatch,
)

from app.agents.orchestrator.classifier import classify_node

from app.agents.orchestrator.dispatchers import (
    DISPATCHER_MAP,
    _dispatch_billing,
    _dispatch_documents,
    _dispatch_compliance,
    _dispatch_banking,
    _dispatch_rag,
    _dispatch_crm,
    _dispatch_hr,
    _dispatch_excel,
    _dispatch_email,
    _dispatch_workflow,
    _dispatch_report,
    _dispatch_skill,
)

__all__ = [
    # State types
    "AgentResult", "MAX_ITERATIONS", "OrchestratorState", "SubTask",
    "TaskStatus", "VALID_DOMAINS",
    # Graph
    "orchestrator", "build_orchestrator", "DISPATCHER_MAP",
    # Nodes
    "classify_node", "plan_node", "validate_node", "dispatch_node",
    "load_knowledge_node", "route_after_validate", "route_after_dispatch",
    # Dispatchers
    "_dispatch_billing", "_dispatch_documents", "_dispatch_compliance",
    "_dispatch_banking", "_dispatch_rag", "_dispatch_crm", "_dispatch_hr",
    "_dispatch_excel", "_dispatch_email", "_dispatch_workflow",
    "_dispatch_report", "_dispatch_skill",
]
