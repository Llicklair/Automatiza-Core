"""
Orquestador central basado en LangGraph.
Implementa el grafo de estado: Classify → LoadKnowledge → Plan → Validate → Dispatch → Result

Los nodos se importan de node_handlers.py.
Los dispatchers, clasificador, utilidades y helpers se importan de módulos dedicados.
"""

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.orchestrator.classifier import classify_node
from app.agents.orchestrator.node_handlers import (
    dispatch_node,
    init_tenant_node,
    load_knowledge_node,
    plan_node,
    summarize_node,
    validate_node,
)
from app.agents.orchestrator.state import (
    MAX_ITERATIONS,
    OrchestratorState,
    TaskStatus,
)


# ─── Routing functions ──────────────────────────────────────────────────────


def route_after_validate(state: OrchestratorState) -> str:
    if state["status"] == TaskStatus.FAILED:
        return "end"
    if state.get("requires_human_approval"):
        return "await_approval"
    return "dispatch"


def route_after_dispatch(state: OrchestratorState) -> str:
    if state["status"] == TaskStatus.FAILED:
        return "end"
    if state["status"] == TaskStatus.DONE:
        return "summarize"
    if state["status"] == TaskStatus.AWAITING_APPROVAL:
        return "end"  # Pausa: esperar aprobación humana antes de continuar
    if state["iteration_count"] >= MAX_ITERATIONS:
        return "end"
    return "dispatch"  # Continúa con siguiente subtarea


# ─── Construcción del grafo ───────────────────────────────────────────────────


def _route_after_load_knowledge(state: OrchestratorState) -> str:
    if state.get("status") == TaskStatus.FAILED:
        return "end"
    return "planner"


def build_orchestrator() -> CompiledStateGraph:
    graph = StateGraph(OrchestratorState)

    graph.add_node("init_tenant", init_tenant_node)
    graph.add_node("classify", classify_node)
    graph.add_node("load_knowledge", load_knowledge_node)
    graph.add_node("planner", plan_node)
    graph.add_node("validate", validate_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("summarize", summarize_node)

    graph.set_entry_point("init_tenant")
    graph.add_conditional_edges(
        "init_tenant",
        lambda s: "end" if s.get("status") == TaskStatus.FAILED else "classify",
        {"classify": "classify", "end": END},
    )
    graph.add_edge("classify", "load_knowledge")
    graph.add_conditional_edges(
        "load_knowledge",
        _route_after_load_knowledge,
        {"planner": "planner", "end": END},
    )
    graph.add_edge("planner", "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "dispatch": "dispatch",
            "await_approval": END,
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "dispatch",
        route_after_dispatch,
        {
            "dispatch": "dispatch",
            "summarize": "summarize",
            "end": END,
        },
    )
    graph.add_edge("summarize", END)

    return graph.compile()


# Instancia global del orquestador compilado
orchestrator = build_orchestrator()
