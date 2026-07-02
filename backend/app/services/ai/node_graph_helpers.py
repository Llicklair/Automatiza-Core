"""
node_graph_helpers — Funciones puras de traversal de grafo para NodeEngine.

Todas las funciones son síncronas y no tocan la BD.
Operan sobre los datos del grafo (nodes, edges, node_states) que se les pasan
como argumentos, manteniendo NodeEngine limpio de lógica estructural.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

# Node statuses (re-exported for convenience)
COMPLETED = "completed"
FAILED = "failed"
RUNNING = "running"
WAITING = "waiting"
PAUSED = "paused"
SKIPPED = "skipped"
PENDING = "pending"

# Advanced node types that trigger the NodeEngine
ADVANCED_NODE_TYPES = {"conditional", "delay", "approval_gate", "parallel"}


def has_advanced_nodes(ui_nodes: list[dict], ui_edges: list[dict] | None = None) -> bool:
    """Returns True if the workflow contains any advanced node types or fan-out topology."""
    from collections import Counter

    if any(n.get("type") in ADVANCED_NODE_TYPES for n in (ui_nodes or [])):
        return True
    if ui_edges:
        source_counts = Counter(e.get("source") for e in ui_edges)
        if any(v >= 2 for v in source_counts.values()):
            return True
    return False


def get_predecessors(edges: list[dict], node_id: str) -> list[str]:
    """Retorna los IDs de nodos que son fuente de aristas hacia este nodo."""
    return [e["source"] for e in edges if e["target"] == node_id]


def get_successors(edges: list[dict], node_id: str) -> list[str]:
    """Retorna los IDs de nodos que son target de aristas desde este nodo."""
    return [e["target"] for e in edges if e["source"] == node_id]


def find_ready_nodes(
    nodes: list[dict],
    edges: list[dict],
    node_states: dict[str, dict],
) -> list[dict]:
    """Encuentra nodos listos para ejecutar: todas sus dependencias están completas."""
    ready = []
    for node in nodes:
        nid = node["id"]
        if nid in node_states and node_states[nid]["status"] in (
            COMPLETED,
            FAILED,
            SKIPPED,
            RUNNING,
            WAITING,
            PAUSED,
        ):
            continue

        predecessors = get_predecessors(edges, nid)
        if predecessors:
            if all(node_states.get(p, {}).get("status") in (COMPLETED, SKIPPED) for p in predecessors):
                ready.append(node)
        else:
            # No predecessors and not a trigger — skip orphan nodes
            if node.get("type") != "trigger":
                continue
            ready.append(node)

    return ready


def all_leaf_nodes_completed(
    nodes: list[dict],
    edges: list[dict],
    node_states: dict[str, dict],
) -> bool:
    """True si todos los leaf nodes (sin sucesores) están completados o skipped."""
    leaf_nodes = [n for n in nodes if not get_successors(edges, n["id"])]
    if not leaf_nodes:
        return False
    return all(node_states.get(n["id"], {}).get("status") in (COMPLETED, SKIPPED, FAILED) for n in leaf_nodes)


def has_suspended_nodes(node_states: dict[str, dict]) -> bool:
    """True si hay algún nodo en estado waiting o paused."""
    return any(ns.get("status") in (WAITING, PAUSED) for ns in node_states.values())


def build_context_for_node(
    edges: list[dict],
    node_states: dict[str, dict],
    node_id: str,
) -> dict:
    """Construye un dict de contexto con los outputs de nodos predecesores."""
    context = {}
    for pid in get_predecessors(edges, node_id):
        if pid in node_states:
            context[pid] = node_states[pid]
    return context


def skip_discarded_branch(
    edges: list[dict],
    node_states: dict[str, dict],
    conditional_node_id: str,
    chosen_branch: str,
) -> None:
    """Marca recursivamente como skipped los nodos de la rama descartada (in-place)."""
    discarded_branch = "false" if chosen_branch == "true" else "true"

    discarded_targets: set[str] = set()
    for edge in edges:
        if edge.get("source") == conditional_node_id:
            edge_branch = (edge.get("data") or {}).get("branch")
            if edge_branch == discarded_branch:
                discarded_targets.add(edge["target"])

    to_skip = list(discarded_targets)
    visited: set[str] = set()
    while to_skip:
        nid = to_skip.pop()
        if nid in visited:
            continue
        visited.add(nid)
        node_states[nid] = {
            "status": SKIPPED,
            "output": {"reason": f"Skipped: branch '{discarded_branch}' from {conditional_node_id}"},
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        }
        for edge in edges:
            if edge.get("source") == nid:
                to_skip.append(edge["target"])


def build_skill_dispatch(
    node: dict,
    edges: list[dict],
    node_states: dict[str, dict],
    tenant_id: str,
    user_id: str | None,
    execution_id: str,
    extra_meta: dict | None = None,
) -> tuple[str, str, dict, dict]:
    """
    Construye (domain, instruction, subtask, mini_state) para despachar un nodo skill.
    Pura — no toca BD ni hace I/O.
    """
    from app.agents.orchestrator import TaskStatus

    data = node.get("data", {})
    domain = data.get("domain", "billing")
    instruction = data.get("instruction") or data.get("label", "Ejecutar automatización")

    prev_outputs = build_context_for_node(edges, node_states, node["id"])
    ctx_parts = [instruction]
    if prev_outputs:
        ctx_parts.append("\n--- Contexto de nodos anteriores ---")
        for nid, ns in prev_outputs.items():
            output = ns.get("output", {})
            if isinstance(output, dict):
                summary = ", ".join(
                    f"{k}: {v}" for k, v in output.items() if not isinstance(v, dict | list) or len(str(v)) < 200
                )
                ctx_parts.append(f"Nodo {nid}: {summary}")
    enriched_intent = "\n".join(ctx_parts)

    meta = {"execution_id": execution_id}
    if extra_meta:
        meta.update(extra_meta)

    subtask_params: dict = {"intent": enriched_intent}
    # Si el nodo tiene employee_id (asignado por parse-nl o por el modal), propágalo
    # a params para que _invoke_dynamic_employee pueda resolver al AIEmployee exacto
    # en lugar de elegir uno random con domain == agent_name.
    if data.get("employee_id"):
        subtask_params["employee_id"] = data["employee_id"]
    subtask = {
        "id": node["id"],
        "agent": domain,
        "action": "execute_node",
        "params": subtask_params,
        "depends_on": [],
        "status": "pending",
    }
    mini_state = {
        "task_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "user_id": user_id or "",
        "user_intent": instruction,
        "current_intent": enriched_intent,
        "classified_domain": domain,
        "plan": [subtask],
        "current_step": 0,
        "agent_results": [],
        "status": TaskStatus.EXECUTING,
        "requires_human_approval": False,
        "approval_id": None,
        "error_message": None,
        "iteration_count": 0,
        "additional_metadata": meta,
    }
    return domain, instruction, subtask, mini_state
