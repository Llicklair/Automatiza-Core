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
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import PendingApproval, Workflow, WorkflowExecution
from app.services.audit import log_action
from app.services.ai.condition_evaluator import evaluate_condition, _resolve_field
from app.services.workflow.task_dispatch import dispatch_resume_node_engine

_logger = logging.getLogger(__name__)

# Node statuses
COMPLETED = "completed"
FAILED = "failed"
RUNNING = "running"
WAITING = "waiting"  # delay
PAUSED = "paused"  # approval_gate
SKIPPED = "skipped"
PENDING = "pending"

# Advanced node types that trigger the NodeEngine
ADVANCED_NODE_TYPES = {"conditional", "delay", "approval_gate", "parallel"}


def has_advanced_nodes(ui_nodes: list[dict], ui_edges: list[dict] | None = None) -> bool:
    """Returns True if the workflow contains any advanced node types or fan-out topology."""
    if any(n.get("type") in ADVANCED_NODE_TYPES for n in (ui_nodes or [])):
        return True
    if ui_edges:
        source_counts = Counter(e.get("source") for e in ui_edges)
        if any(v >= 2 for v in source_counts.values()):
            return True
    return False


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
        # 1. Load workflow definition
        wf = await self._load_workflow(db)
        if not wf:
            return {"status": "failed", "error": "Workflow not found"}

        self.nodes = wf.ui_nodes or []
        self.edges = wf.ui_edges or []
        self.node_map = {n["id"]: n for n in self.nodes}

        # 2. Load execution and existing node_states (for resume)
        execution = await self._load_execution(db)
        if not execution:
            return {"status": "failed", "error": "Execution not found"}

        self.node_states = dict(execution.node_states or {})

        # 3. Mark trigger node(s) as completed
        for node in self.nodes:
            if node.get("type") == "trigger" and node["id"] not in self.node_states:
                self.node_states[node["id"]] = {
                    "status": COMPLETED,
                    "output": self.trigger_payload,
                    "started_at": datetime.now(UTC).isoformat(),
                    "completed_at": datetime.now(UTC).isoformat(),
                }

        # 4. Update execution status to running
        execution.status = "running"
        execution.node_states = dict(self.node_states)
        await db.flush()

        # 5. Execute the graph loop
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

        # Mark the paused/waiting node as completed for resume
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
        max_iterations = 100  # Safety limit

        for _ in range(max_iterations):
            ready_nodes = self._find_ready_nodes()

            if not ready_nodes:
                # Check if we're done or stuck
                if self._all_leaf_nodes_completed():
                    execution.status = "success"
                    execution.completed_at = datetime.now(UTC)
                    execution.node_states = dict(self.node_states)
                    execution.current_node_id = None
                    await db.commit()
                    return {"status": "success", "node_states": self.node_states}

                # Check if any node is waiting/paused (suspension)
                if self._has_suspended_nodes():
                    execution.node_states = dict(self.node_states)
                    await db.commit()
                    return {"status": execution.status, "node_states": self.node_states}

                # No ready nodes and not all done — something went wrong
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

            # Execute ready nodes: sequential for single, parallel for multiple
            if len(ready_nodes) == 1:
                # Single node — existing sequential path
                node = ready_nodes[0]
                execution.current_node_id = node["id"]
                execution.node_states = dict(self.node_states)
                await db.flush()

                result = await self._execute_node(node, db)

                if result.get("suspend"):
                    # Node requested suspension (delay or approval gate)
                    execution.node_states = dict(self.node_states)
                    await db.commit()
                    return {"status": execution.status, "node_states": self.node_states}
            else:
                # Multiple ready nodes — parallel execution via asyncio.gather
                now = datetime.now(UTC).isoformat()
                # Mark all as RUNNING before dispatching
                for node in ready_nodes:
                    self.node_states[node["id"]] = {
                        "status": RUNNING,
                        "started_at": now,
                        "output": None,
                        "completed_at": None,
                    }
                execution.node_states = dict(self.node_states)
                await db.flush()

                # Run agent work in parallel (each call uses its own DB session internally)
                parallel_results = await asyncio.gather(
                    *[self._run_agent_parallel(node) for node in ready_nodes],
                    return_exceptions=True,
                )

                # Serialize state updates back to db
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

        # Safety limit reached
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
            if node_type == "skill":
                output = await self._execute_skill_node(node, db)
                self.node_states[node_id]["status"] = COMPLETED
                self.node_states[node_id]["output"] = output
                self.node_states[node_id]["completed_at"] = datetime.now(UTC).isoformat()
                return {}

            elif node_type == "conditional":
                branch = self._execute_conditional_node(node)
                self.node_states[node_id]["status"] = COMPLETED
                self.node_states[node_id]["output"] = {"branch": branch}
                self.node_states[node_id]["completed_at"] = datetime.now(UTC).isoformat()
                # Skip nodes on the discarded branch
                self._skip_discarded_branch(node_id, branch)
                return {}

            elif node_type == "delay":
                return await self._execute_delay_node(node, db)

            elif node_type == "approval_gate":
                return await self._execute_approval_gate(node, db)

            elif node_type == "trigger":
                # Already marked as completed
                self.node_states[node_id]["status"] = COMPLETED
                self.node_states[node_id]["completed_at"] = datetime.now(UTC).isoformat()
                return {}

            else:
                # Treat unknown types as skill nodes
                output = await self._execute_skill_node(node, db)
                self.node_states[node_id]["status"] = COMPLETED
                self.node_states[node_id]["output"] = output
                self.node_states[node_id]["completed_at"] = datetime.now(UTC).isoformat()
                return {}

        except Exception as e:
            self.node_states[node_id]["status"] = FAILED
            self.node_states[node_id]["output"] = {"error": str(e)}
            self.node_states[node_id]["completed_at"] = datetime.now(UTC).isoformat()

            # Log the failure
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

    def _build_skill_dispatch(
        self, node: dict, extra_meta: dict | None = None
    ) -> tuple[str, str, dict, dict]:
        """Construye (domain, instruction, subtask, mini_state) para despachar un nodo skill."""
        from app.agents.orchestrator import TaskStatus

        data = node.get("data", {})
        domain = data.get("domain", "billing")
        instruction = data.get("instruction") or data.get("label", "Ejecutar automatización")

        prev_outputs = self._build_context_for_node(node["id"])
        ctx_parts = [instruction]
        if prev_outputs:
            ctx_parts.append("\n--- Contexto de nodos anteriores ---")
            for nid, ns in prev_outputs.items():
                output = ns.get("output", {})
                if isinstance(output, dict):
                    summary = ", ".join(
                        f"{k}: {v}"
                        for k, v in output.items()
                        if not isinstance(v, (dict, list)) or len(str(v)) < 200
                    )
                    ctx_parts.append(f"Nodo {nid}: {summary}")
        enriched_intent = "\n".join(ctx_parts)

        meta = {"execution_id": self.execution_id}
        if extra_meta:
            meta.update(extra_meta)

        subtask = {
            "id": node["id"],
            "agent": domain,
            "action": "execute_node",
            "params": {"intent": enriched_intent},
            "depends_on": [],
            "status": "pending",
        }
        mini_state = {
            "task_id": str(uuid.uuid4()),
            "tenant_id": self.tenant_id,
            "user_id": self.user_id or "",
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

    async def _execute_skill_node(self, node: dict, db: AsyncSession) -> dict:
        """Ejecuta un nodo skill reutilizando las funciones _dispatch_* del orchestrator."""
        domain, instruction, subtask, mini_state = self._build_skill_dispatch(node)
        result = await self._dispatch_agent(domain, mini_state, subtask)

        try:
            action_str = (
                result.get("output", {}).get("action", "execute")
                if isinstance(result.get("output"), dict)
                else "execute"
            )
            await log_action(
                db,
                tenant_id=uuid.UUID(self.tenant_id),
                agent_name=domain,
                action_type=action_str,
                status="success" if result.get("success") else "failed",
                input_data={"node_id": node["id"], "instruction": instruction},
                output_data=result.get("output"),
                error_detail=result.get("error"),
            )
            await db.flush()
        except Exception:
            _logger.warning(
                "Failed to audit skill node execution for node %s", node["id"], exc_info=True
            )

        return result.get("output", {})

    async def _run_agent_parallel(self, node: dict) -> dict:
        """
        Ejecuta un nodo skill sin sesión DB compartida (para asyncio.gather).
        Devuelve el dict node_state actualizado.
        """
        node_type = node.get("type", "skill")
        now = datetime.now(UTC).isoformat()

        if node_type not in ("skill", "action", "trigger"):
            return {
                "status": SKIPPED,
                "started_at": now,
                "output": {"reason": f"Node type '{node_type}' not parallelizable"},
                "completed_at": datetime.now(UTC).isoformat(),
            }
        if node_type == "trigger":
            return {
                "status": COMPLETED,
                "started_at": now,
                "output": self.trigger_payload,
                "completed_at": datetime.now(UTC).isoformat(),
            }

        try:
            domain, _instruction, subtask, mini_state = self._build_skill_dispatch(
                node, extra_meta={"parallel": True}
            )
            result = await self._dispatch_agent(domain, mini_state, subtask)
            return {
                "status": COMPLETED if result.get("success", True) else FAILED,
                "started_at": now,
                "output": result.get("output", {}),
                "completed_at": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            return {
                "status": FAILED,
                "started_at": now,
                "output": {"error": str(e)},
                "completed_at": datetime.now(UTC).isoformat(),
            }

    async def _dispatch_agent(self, domain: str, state: dict, subtask: dict) -> dict:
        """Dispatch to the appropriate agent based on domain."""
        from app.agents.orchestrator.dispatchers import (
            _dispatch_banking,
            _dispatch_billing,
            _dispatch_compliance,
            _dispatch_crm,
            _dispatch_documents,
            _dispatch_email,
            _dispatch_excel,
            _dispatch_hr,
            _dispatch_rag,
            _dispatch_skill,
            _dispatch_workflow,
        )

        dispatch_map = {
            "billing": _dispatch_billing,
            "documents": _dispatch_documents,
            "hr": _dispatch_hr,
            "email": _dispatch_email,
            "crm": _dispatch_crm,
            "banking": _dispatch_banking,
            "compliance": _dispatch_compliance,
            "rag": _dispatch_rag,
            "excel": _dispatch_excel,
            "workflow": _dispatch_workflow,
            "skill": _dispatch_skill,
        }

        try:
            lookup = domain if not domain.startswith("skill:") else "skill"
            handler = dispatch_map.get(lookup)
            if not handler:
                return {
                    "subtask_id": subtask["id"],
                    "agent": domain,
                    "success": False,
                    "output": {"message": f"Agente '{domain}' no reconocido"},
                    "error": f"Unknown domain: {domain}",
                }
            return await handler(state, subtask)
        except Exception as e:
            return {
                "subtask_id": subtask["id"],
                "agent": domain,
                "success": False,
                "output": {"error": str(e)},
                "error": str(e),
            }

    def _execute_conditional_node(self, node: dict) -> str:
        """Evalúa la condición y devuelve 'true' o 'false'."""
        data = node.get("data", {})
        condition = data.get("condition", {})

        # Build context from predecessor outputs
        context = self._build_context_for_node(node["id"])

        # Add 'prev' shortcut pointing to the most recent predecessor
        predecessors = self._get_predecessors(node["id"])
        if predecessors:
            last_pred = predecessors[-1]
            if last_pred in self.node_states:
                context["prev"] = self.node_states[last_pred]

        _logger.info(
            f"[CONDITIONAL] node={node['id']} condition={condition} "
            f"context_keys={list(context.keys())}"
        )
        # Log the resolved field value for debugging
        field = condition.get("field", "")
        resolved = _resolve_field(field, context)
        _logger.info(
            f"[CONDITIONAL] field='{field}' resolved_to={resolved}"
        )

        result = evaluate_condition(condition, context)
        return "true" if result else "false"

    async def _execute_delay_node(self, node: dict, db: AsyncSession) -> dict:
        """Programa un resume tras delay_seconds."""
        data = node.get("data", {})
        delay_seconds = int(data.get("delay_seconds", 10))
        node_id = node["id"]

        self.node_states[node_id]["status"] = WAITING
        self.node_states[node_id]["output"] = {"delay_seconds": delay_seconds}

        # Load execution and update
        execution = await self._load_execution(db)
        if execution:
            execution.status = "running"  # Stays running during delays
            execution.current_node_id = node_id
            execution.node_states = dict(self.node_states)
            await db.flush()

        # Schedule task to resume after delay
        try:
            await dispatch_resume_node_engine(
                self.execution_id,
                node_id,
                delay_seconds=delay_seconds,
            )
        except Exception as e:
            _logger.error("Error scheduling delay resume: %s", e)

        return {"suspend": True}

    async def _execute_approval_gate(self, node: dict, db: AsyncSession) -> dict:
        """Crea PendingApproval y pausa la ejecución."""

        data = node.get("data", {})
        description = (
            data.get("description") or data.get("label") or "Aprobación requerida para continuar"
        )
        node_id = node["id"]

        self.node_states[node_id]["status"] = PAUSED
        self.node_states[node_id]["output"] = {"description": description}

        # Create PendingApproval
        approval = PendingApproval(
            task_id=uuid.uuid4(),  # Placeholder — no linked task in node engine
            tenant_id=uuid.UUID(self.tenant_id),
            execution_id=uuid.UUID(self.execution_id),
            action_description=description,
            action_payload={"node_id": node_id, "execution_id": self.execution_id},
            risk_level="medium",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            status="pending",
        )
        db.add(approval)
        await db.flush()

        # Update execution to paused
        execution = await self._load_execution(db)
        if execution:
            execution.status = "paused"
            execution.paused_at = datetime.now(UTC)
            execution.current_node_id = node_id
            execution.node_states = dict(self.node_states)
            await db.flush()

        return {"suspend": True}

    def _skip_discarded_branch(self, conditional_node_id: str, chosen_branch: str):
        """Marca recursivamente como skipped los nodos de la rama descartada."""
        discarded_branch = "false" if chosen_branch == "true" else "true"

        # Find edges from the conditional node for the discarded branch
        discarded_targets = set()
        for edge in self.edges:
            if edge.get("source") == conditional_node_id:
                edge_branch = (edge.get("data") or {}).get("branch")
                if edge_branch == discarded_branch:
                    discarded_targets.add(edge["target"])

        # Recursively skip all descendants on the discarded branch
        to_skip = list(discarded_targets)
        visited = set()
        while to_skip:
            nid = to_skip.pop()
            if nid in visited:
                continue
            visited.add(nid)
            self.node_states[nid] = {
                "status": SKIPPED,
                "output": {
                    "reason": f"Skipped: branch '{discarded_branch}' from {conditional_node_id}"
                },
                "started_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            }
            # Find children of this node
            for edge in self.edges:
                if edge.get("source") == nid:
                    to_skip.append(edge["target"])

    def _find_ready_nodes(self) -> list[dict]:
        """Encuentra nodos listos para ejecutar: todas sus dependencias están completas."""
        ready = []
        for node in self.nodes:
            nid = node["id"]
            # Skip already processed nodes
            if nid in self.node_states and self.node_states[nid]["status"] in (
                COMPLETED,
                FAILED,
                SKIPPED,
                RUNNING,
                WAITING,
                PAUSED,
            ):
                continue

            # Check all predecessors are completed or skipped
            predecessors = self._get_predecessors(nid)
            if (
                all(
                    self.node_states.get(p, {}).get("status") in (COMPLETED, SKIPPED)
                    for p in predecessors
                )
                if predecessors
                else not predecessors
            ):
                # Node with no predecessors and not a trigger (triggers are pre-completed)
                if not predecessors and node.get("type") != "trigger":
                    # This could be an orphan node — skip it
                    continue
                ready.append(node)

        return ready

    def _get_predecessors(self, node_id: str) -> list[str]:
        """Retorna los IDs de nodos que son fuente de aristas hacia este nodo."""
        return [e["source"] for e in self.edges if e["target"] == node_id]

    def _get_successors(self, node_id: str) -> list[str]:
        """Retorna los IDs de nodos que son target de aristas desde este nodo."""
        return [e["target"] for e in self.edges if e["source"] == node_id]

    def _all_leaf_nodes_completed(self) -> bool:
        """True si todos los leaf nodes (sin sucesores) están completados o skipped."""
        leaf_nodes = [n for n in self.nodes if not self._get_successors(n["id"])]
        if not leaf_nodes:
            return False
        return all(
            self.node_states.get(n["id"], {}).get("status") in (COMPLETED, SKIPPED, FAILED)
            for n in leaf_nodes
        )

    def _has_suspended_nodes(self) -> bool:
        """True si hay algún nodo en estado waiting o paused."""
        return any(ns.get("status") in (WAITING, PAUSED) for ns in self.node_states.values())

    def _build_context_for_node(self, node_id: str) -> dict:
        """Construye un dict de contexto con los outputs de nodos predecesores."""
        context = {}
        predecessors = self._get_predecessors(node_id)
        for pid in predecessors:
            if pid in self.node_states:
                context[pid] = self.node_states[pid]
        return context

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
