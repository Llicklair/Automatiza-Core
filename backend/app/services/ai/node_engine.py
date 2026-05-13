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
from app.services.ai import node_engine_nodes as _nodes
from app.services.ai.node_graph_helpers import (
    COMPLETED,
    FAILED,
    RUNNING,
    all_leaf_nodes_completed,
    find_ready_nodes,
    get_predecessors,
    get_successors,
    has_suspended_nodes,
    skip_discarded_branch,
)
from app.services.audit import log_action

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

        from app.services.ai.node_graph_helpers import PAUSED, WAITING

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

    async def _emit_node_event(self, payload: dict) -> None:
        """Broadcast WS de progreso de nodo del workflow.
        Silencioso en errores — no debe romper la ejecución.

        Además del payload original, cuando es completed/failed emite un
        evento sintético `activity_new` para que el feed de actividad de
        la bandeja se actualice en vivo (sin esperar a polling).
        """
        try:
            from app.api.ws.notifications import manager as ws_manager
            await ws_manager.broadcast_to_tenant(self.tenant_id, payload)
            # Mirror a activity_new para llenar el feed en vivo. Solo eventos
            # terminales — los "started" saturarían el feed.
            ev_type = payload.get("type")
            if ev_type in ("workflow_node_completed", "workflow_node_failed"):
                is_ok = ev_type == "workflow_node_completed"
                node_label = payload.get("label") or "Nodo"
                summary = payload.get("result_summary") or payload.get("error") or ""
                synthetic_entry = {
                    "id": f"wf-{payload.get('node_id')}-{payload.get('completed_at')}",
                    "employee_id": None,
                    "category": "workflow",
                    "icon": "✅" if is_ok else "❌",
                    "message": f"[{self.workflow_id[:8]}] {node_label}: {summary[:120]}",
                    "metadata": {
                        "workflow_id": self.workflow_id,
                        "execution_id": self.execution_id,
                        "node_id": payload.get("node_id"),
                    },
                    "created_at": payload.get("completed_at"),
                }
                await ws_manager.broadcast_to_tenant(
                    self.tenant_id,
                    {"type": "activity_new", "entry": synthetic_entry},
                )
        except Exception:
            pass

    async def _execute_node(self, node: dict, db: AsyncSession) -> dict:
        """Despacha según type: skill, conditional, delay, approval_gate."""
        node_id = node["id"]
        node_type = node.get("type", "skill")
        now = datetime.now(UTC).isoformat()

        # Extraer info legible del nodo para el frontend
        node_data = node.get("data", {}) or {}
        node_label = node_data.get("label") or node_data.get("description") or node_type
        node_agent = (
            node_data.get("domain")
            or node_data.get("agent")
            or node_data.get("skill")
            or node_type
        )
        node_instruction = (
            node_data.get("instruction")
            or node_data.get("description")
            or node_data.get("label")
            or ""
        )

        self.node_states[node_id] = {
            "status": RUNNING,
            "started_at": now,
            "output": None,
            "completed_at": None,
        }

        # Emit "started"
        await self._emit_node_event({
            "type": "workflow_node_started",
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "node_id": node_id,
            "node_type": node_type,
            "label": str(node_label)[:100],
            "agent": str(node_agent)[:50],
            "instruction": str(node_instruction)[:200],
            "started_at": now,
        })

        try:
            if node_type == "skill" or node_type not in (
                "conditional",
                "delay",
                "approval_gate",
                "trigger",
            ):
                output = await _nodes.execute_skill_node(self, node, db)
                completed_at = datetime.now(UTC).isoformat()
                self.node_states[node_id]["status"] = COMPLETED
                self.node_states[node_id]["output"] = output
                self.node_states[node_id]["completed_at"] = completed_at

                # Detectar si el skill disparó "aprobación humana requerida"
                # y crear PendingApproval enlazado al workflow execution.
                try:
                    from app.agents.orchestrator.helpers import (
                        _ensure_pending_approval,
                        _response_indicates_approval,
                    )
                    output_text = ""
                    if isinstance(output, dict):
                        output_text = (
                            output.get("response")
                            or output.get("summary")
                            or output.get("result")
                            or ""
                        )
                    elif isinstance(output, str):
                        output_text = output
                    if output_text and _response_indicates_approval(output_text):
                        await _ensure_pending_approval(
                            tenant_id=self.tenant_id,
                            execution_id=self.execution_id,
                            agent_results=[{
                                "agent": str(node_agent),
                                "output": {"response": output_text},
                                "summary": output_text[:200],
                            }],
                        )
                except Exception:
                    _logger.warning(
                        "Error creando PendingApproval para workflow execution %s",
                        self.execution_id, exc_info=True,
                    )

                await self._emit_node_event({
                    "type": "workflow_node_completed",
                    "execution_id": self.execution_id,
                    "node_id": node_id,
                    "completed_at": completed_at,
                    "result_summary": str(output)[:200] if output else "",
                })
                return {}

            elif node_type == "conditional":
                branch = _nodes.execute_conditional_node(self, node)
                completed_at = datetime.now(UTC).isoformat()
                self.node_states[node_id]["status"] = COMPLETED
                self.node_states[node_id]["output"] = {"branch": branch}
                self.node_states[node_id]["completed_at"] = completed_at
                skip_discarded_branch(self.edges, self.node_states, node_id, branch)
                await self._emit_node_event({
                    "type": "workflow_node_completed",
                    "execution_id": self.execution_id,
                    "node_id": node_id,
                    "completed_at": completed_at,
                    "result_summary": f"Rama tomada: {branch}",
                })
                return {}

            elif node_type == "delay":
                return await _nodes.execute_delay_node(self, node, db)

            elif node_type == "approval_gate":
                return await _nodes.execute_approval_gate(self, node, db)

            elif node_type == "trigger":
                completed_at = datetime.now(UTC).isoformat()
                self.node_states[node_id]["status"] = COMPLETED
                self.node_states[node_id]["completed_at"] = completed_at
                await self._emit_node_event({
                    "type": "workflow_node_completed",
                    "execution_id": self.execution_id,
                    "node_id": node_id,
                    "completed_at": completed_at,
                    "result_summary": "Trigger procesado",
                })
                return {}

        except Exception as e:
            completed_at = datetime.now(UTC).isoformat()
            self.node_states[node_id]["status"] = FAILED
            self.node_states[node_id]["output"] = {"error": str(e)}
            self.node_states[node_id]["completed_at"] = completed_at
            await self._emit_node_event({
                "type": "workflow_node_failed",
                "execution_id": self.execution_id,
                "node_id": node_id,
                "completed_at": completed_at,
                "error": str(e)[:200],
            })

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

        return {}  # unreachable but satisfies mypy

    # ── convenience wrappers kept for callers that reference self._ methods ──

    def _build_skill_dispatch(self, node: dict, extra_meta: dict | None = None):
        from app.services.ai.node_graph_helpers import build_skill_dispatch

        return build_skill_dispatch(
            node,
            self.edges,
            self.node_states,
            self.tenant_id,
            self.user_id,
            self.execution_id,
            extra_meta,
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
        # Filtro por tenant: defensa en profundidad. La validación primaria ocurre
        # upstream en run_workflow(); esto la respalda y será obligatorio bajo RLS.
        result = await db.execute(
            select(Workflow).where(
                Workflow.id == uuid.UUID(self.workflow_id),
                Workflow.tenant_id == uuid.UUID(self.tenant_id),
            )
        )
        return result.scalar_one_or_none()

    async def _load_execution(self, db: AsyncSession) -> WorkflowExecution | None:
        result = await db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.id == uuid.UUID(self.execution_id),
                WorkflowExecution.tenant_id == uuid.UUID(self.tenant_id),
            )
        )
        return result.scalar_one_or_none()
