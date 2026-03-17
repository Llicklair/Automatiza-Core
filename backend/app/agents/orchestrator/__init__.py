"""
Paquete del orquestador — mantiene compatibilidad con imports existentes.

Antes:  from app.agents.orchestrator import orchestrator, OrchestratorState, ...
Ahora:  misma sintaxis, funciona igual.

Estructura:
  orchestrator/
    state.py    — Tipos: TaskStatus, SubTask, AgentResult, OrchestratorState
    _core.py    — Lógica del grafo: nodos, dispatchers, build_orchestrator
    __init__.py — Re-exporta todo (este archivo)
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
    classify_node,
    plan_node,
    validate_node,
    dispatch_node,
    load_knowledge_node,
    route_after_validate,
    route_after_dispatch,
    # Dispatchers individuales (usados por node_engine)
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
    "orchestrator", "build_orchestrator",
    # Nodes
    "classify_node", "plan_node", "validate_node", "dispatch_node",
    "load_knowledge_node", "route_after_validate", "route_after_dispatch",
    # Dispatchers
    "_dispatch_billing", "_dispatch_documents", "_dispatch_compliance",
    "_dispatch_banking", "_dispatch_rag", "_dispatch_crm", "_dispatch_hr",
    "_dispatch_excel", "_dispatch_email", "_dispatch_workflow",
    "_dispatch_report", "_dispatch_skill",
]
