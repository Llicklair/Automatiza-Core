"""
NodeEngine — Motor de ejecución de grafos para workflows con nodos de control de flujo.

Ejecuta un grafo de workflow nodo a nodo con soporte para:
  - trigger: nodo inicial (schedule, event, manual)
  - skill: ejecuta un agente completo (billing, hr, email, etc.)
  - conditional: bifurca según condición sobre output previo
  - delay: espera N segundos (suspende y programa reanudación)
  - approval_gate: pausa hasta aprobación humana

Flujo:
  1. Carga Workflow.ui_nodes y ui_edges
  2. Carga node_states existentes (para resume)
  3. Marca trigger como completed
  4. Loop: busca nodos listos → ejecuta → actualiza node_states en BD
  5. Si delay/approval → suspende, programa reanudación/crea PendingApproval
  6. Todos los leaf nodes completados → execution.status = "success"

Graph traversal helpers live in node_graph_helpers.py (pure, sync, no DB).
Node-type execution handlers live in node_engine_nodes.py.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Workflow, WorkflowExecution
from app.services.audit import log_action
from app.services.ai.node_graph_helpers import (
    COMPLETED, FAILED, RUNNING, SKIPPED,
    all_leaf_nodes_completed,
    find_ready_nodes,
    get_predecessors,
    get_successors,
    has_suspended_nodes,
    skip_discarded_branch,
)
from app.services.ai import node_engine_nodes as _nodes

_logger = logging.getLogger(__name__)


class NodeEngine:
    """Ejecuta un grafo de workflow nodo a nodo."""

    def __init__(
        self,
        workflow_id: str,
        execution_id: str,
        tenant_id: str,
        user_id: str | None,
        trigger_payload: dict | None = None,
    ):
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.trigger_payload = trigger_payload or {}

        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self.node_map: dict[str, dict] = {}
        self.node_states: dict[str, dict] = {}

    async def run(self, db: AsyncSession) -> dict:
        """Ejecuta el grafo completo desde el inicio."""
        wf = await self._load_workflow(db)
        if not wf:
            return {"status": "failed", "error": "Workflow not found"}

        self.nodes = wf.ui_nodes or []
        self.edges = wf.ui_edges or []
        self.node_map = {n["id"]: n for n in self.nodes}

        execution = await self._load_execution(db)
        if not execution:
            return {"status": "failed", "error": "Execution not found"}

        self.node_states = dict(execution.node_states or {})

        for node in self.nodes:
            if node.get("type") == "trigger" and node["id"] not in self.node_states:
                self.node_states[node["id"]] = {
                    "status": COMPLETED,
                    "output": self.trigger_payload,
                    "started_at": datetime.now(UTC).isoformat(),
                    "completed_at": datetime.now(UTC).isoformat(),
                }

        execution.status = "running"
        execution.node_states = dict(self.node_states)
        await db.flush()

        return await self._execute_loop(db, execution)

    async def resume(self, db: AsyncSession, from_node_id: str) -> dict:
        """Reanuda desde un nodo pausado/esperando."""
        wf = await self._load_workflow(db)
        if not wf:
            return {"status": "failed", "error": "Workflow not found"}

        self.nodes = wf.ui_nodes or []
        self.edges = wf.ui_edges or []
        self.node_map = {n["id"]: n for n in self.nodes}

        execution = await self._load_execution(db)
        if not execution:
            return {"status": "failed", "error": "Execution not found"}

        self.node_states = dict(execution.node_states or {})

        from app.services.ai.node_graph_helpers import WAITING, PAUSED
        if from_node_id in self.node_states:
            ns = self.node_states[from_node_id]
            if ns["status"] in (WAITING, PAUSED):
                ns["status"] = COMPLETED
                ns["completed_at"] = datetime.now(UTC).isoformat()

        execution.status = "running"
        execution.paused_at = None
        execution.node_states = dict(self.node_states)
        await db.flush()

        return await self._execute_loop(db, execution)

    async def _execute_loop(self, db: AsyncSession, execution: WorkflowExecution) -> dict:
        """Main execution loop: find ready nodes, execute, repeat."""
        max_iterations = 100

        for _ in range(max_iterations):
            ready_nodes = find_ready_nodes(self.nodes, self.edges, self.node_states)

            if not ready_nodes:
                if all_leaf_nodes_completed(self.nodes, self.edges, self.node_states):
                    execution.status = "success"
                    execution.completed_at = datetime.now(UTC)
                    execution.node_states = dict(self.node_states)
                    execution.current_node_id = None
                    await db.commit()
                    return {"status": "success", "node_states": self.node_states}

                if has_suspended_nodes(self.node_states):
                    execution.node_states = dict(self.node_states)
                    await db.commit()
                    return {"status": execution.status, "node_states": self.node_states}

                execution.status = "failed"
                execution.completed_at = datetime.now(UTC)
                execution.node_states = dict(self.node_states)
                execution.current_node_id = None
                await db.commit()
                return {
                    "status": "failed",
                    "error": "Graph stuck: no ready nodes",
                    "node_states": self.node_states,
                }

            if len(ready_nodes) == 1:
                node = ready_nodes[0]
                execution.current_node_id = node["id"]
                execution.node_states = dict(self.node_states)
                await db.flush()

                result = await self._execute_node(node, db)

                if result.get("suspend"):
                    execution.node_states = dict(self.node_states)
                    await db.commit()
                    return {"status": execution.status, "node_states": self.node_states}
            else:
                now = datetime.now(UTC).isoformat()
                for node in ready_nodes:
                    self.node_states[node["id"]] = {
                        "status": RUNNING,
                        "started_at": now,
                        "output": None,
                        "completed_at": None,
                    }
                execution.node_states = dict(self.node_states)
                await db.flush()

                parallel_results = await asyncio.gather(
                    *[_nodes.run_agent_parallel(self, node) for node in ready_nodes],
                    return_exceptions=True,
                )

                has_suspend = False
                for node, res in zip(ready_nodes, parallel_results):
                    nid = node["id"]
                    if isinstance(res, Exception):
                        self.node_states[nid] = {
                            "status": FAILED,
                            "started_at": self.node_states[nid].get("started_at", now),
                            "output": {"error": str(res)},
                            "completed_at": datetime.now(UTC).isoformat(),
                        }
                    elif isinstance(res, dict) and res.get("suspend"):
                        has_suspend = True
                    elif isinstance(res, dict):
                        self.node_states[nid] = res

                execution.node_states = dict(self.node_states)
                await db.flush()

                if has_suspend:
                    await db.commit()
                    return {"status": execution.status, "node_states": self.node_states}

        execution.status = "failed"
        execution.completed_at = datetime.now(UTC)
        execution.node_states = dict(self.node_states)
        await db.commit()
        return {
            "status": "failed",
            "error": "Max iterations reached",
            "node_states": self.node_states,
        }

    async def _execute_node(self, node: dict, db: AsyncSession) -> dict:
        """Despacha según type: skill, conditional, delay, approval_gate."""
        node_id = node["id"]
        node_type = node.get("type", "skill")
        now = datetime.now(UTC).isoformat()

        self.node_states[node_id] = {
            "status": RUNNING,
            "started_at": now,
            "output": None,
            "completed_at": None,
        }

        try:
            if node_type == "skill" or node_type not in ("conditional", "delay", "approval_gate", "trigger"):
                output = await _nodes.execute_skill_node(self, node, db)
                self.node_states[node_id]["status"] = COMPLETED
                self.node_states[node_id]["output"] = output
                self.node_states[node_id]["completed_at"] = datetime.now(UTC).isoformat()
                return {}

            elif node_type == "conditional":
                branch = _nodes.execute_conditional_node(self, node)
                self.node_states[node_id]["status"] = COMPLETED
                self.node_states[node_id]["output"] = {"branch": branch}
                self.node_states[node_id]["completed_at"] = datetime.now(UTC).isoformat()
                skip_discarded_branch(self.edges, self.node_states, node_id, branch)
                return {}

            elif node_type == "delay":
                return await _nodes.execute_delay_node(self, node, db)

            elif node_type == "approval_gate":
                return await _nodes.execute_approval_gate(self, node, db)

            elif node_type == "trigger":
                self.node_states[node_id]["status"] = COMPLETED
                self.node_states[node_id]["completed_at"] = datetime.now(UTC).isoformat()
                return {}

        except Exception as e:
            self.node_states[node_id]["status"] = FAILED
            self.node_states[node_id]["output"] = {"error": str(e)}
            self.node_states[node_id]["completed_at"] = datetime.now(UTC).isoformat()

            try:
                await log_action(
                    db,
                    tenant_id=uuid.UUID(self.tenant_id),
                    agent_name=f"node_engine:{node_type}",
                    action_type="node_execution_failed",
                    status="failed",
                    input_data={"node_id": node_id, "node_type": node_type},
                    output_data={"error": str(e)},
                    error_detail=str(e),
                )
                await db.flush()
            except Exception:
                _logger.warning(
                    "Failed to audit node_execution_failed for node %s", node_id, exc_info=True
                )

            return {}

    # ── convenience wrappers kept for callers that reference self._ methods ──

    def _build_skill_dispatch(self, node: dict, extra_meta: dict | None = None):
        from app.services.ai.node_graph_helpers import build_skill_dispatch
        return build_skill_dispatch(
            node, self.edges, self.node_states,
            self.tenant_id, self.user_id, self.execution_id, extra_meta,
        )

    def _skip_discarded_branch(self, conditional_node_id: str, chosen_branch: str):
        skip_discarded_branch(self.edges, self.node_states, conditional_node_id, chosen_branch)

    def _find_ready_nodes(self) -> list[dict]:
        return find_ready_nodes(self.nodes, self.edges, self.node_states)

    def _get_predecessors(self, node_id: str) -> list[str]:
        return get_predecessors(self.edges, node_id)

    def _get_successors(self, node_id: str) -> list[str]:
        return get_successors(self.edges, node_id)

    def _all_leaf_nodes_completed(self) -> bool:
        return all_leaf_nodes_completed(self.nodes, self.edges, self.node_states)

    def _has_suspended_nodes(self) -> bool:
        return has_suspended_nodes(self.node_states)

    async def _load_workflow(self, db: AsyncSession) -> Workflow | None:
        result = await db.execute(
            select(Workflow).where(Workflow.id == uuid.UUID(self.workflow_id))
        )
        return result.scalar_one_or_none()

    async def _load_execution(self, db: AsyncSession) -> WorkflowExecution | None:
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == uuid.UUID(self.execution_id))
        )
        return result.scalar_one_or_none()
