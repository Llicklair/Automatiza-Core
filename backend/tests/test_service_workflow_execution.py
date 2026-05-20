"""Tests para app.services.workflow._execution.

Cubre el núcleo de ejecución de workflows (run_workflow, cancel_execution,
deterministic steps). Los caminos que invocan workers reales (Celery,
task_runner) se mockean — esos tests integrales viven en otros archivos.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.db.models.models import Tenant, Workflow, WorkflowExecution
from app.services.workflow._execution import (
    _build_ai_instruction,
    _infer_domain,
    _run_deterministic_step,
    cancel_execution,
    execute_deterministic_steps,
    run_workflow,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _mk_workflow(tenant_id, **overrides):
    """Workflow stub para tests de helpers (no toca DB)."""
    base = dict(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Test WF",
        description=None,
        is_active=True,
        trigger_type="manual",
        action_type="prompt",
        action_config={},
        execution_mode="reasoning",
        compiled_steps=None,
        ui_nodes=None,
        ui_edges=None,
    )
    base.update(overrides)
    return Workflow(**base)


@pytest.fixture
async def _tenant(db):
    t = Tenant(id=uuid4(), name="Test Exec", nif=f"E{uuid4().int % 10**8:08d}")
    db.add(t)
    await db.commit()
    return t


# ── Pure helpers ─────────────────────────────────────────────────────────────


class TestBuildAiInstruction:
    def test_usa_instruction_si_existe(self):
        wf = _mk_workflow(uuid4(), action_config={"instruction": "Haz X"})
        assert _build_ai_instruction(wf) == "Haz X"

    def test_fallback_a_intent(self):
        wf = _mk_workflow(uuid4(), action_config={"intent": "Haz Y"})
        assert _build_ai_instruction(wf) == "Haz Y"

    def test_fallback_a_description(self):
        wf = _mk_workflow(uuid4(), description="Descripción del workflow", action_config={})
        assert _build_ai_instruction(wf) == "Descripción del workflow"

    def test_fallback_a_name(self):
        wf = _mk_workflow(uuid4(), name="Mi workflow", description=None, action_config={})
        assert _build_ai_instruction(wf) == "Mi workflow"

    def test_default_final_si_todo_None(self):
        wf = _mk_workflow(uuid4(), name="", description=None, action_config={})
        assert _build_ai_instruction(wf) == "Ejecutar automatizacion"

    def test_action_config_None_no_crashea(self):
        wf = _mk_workflow(uuid4(), action_config=None)
        # No debe lanzar AttributeError
        result = _build_ai_instruction(wf)
        assert isinstance(result, str)


class TestInferDomain:
    def test_coordinator_si_agent_coordinator(self):
        wf = _mk_workflow(uuid4(), action_config={"agent": "coordinator"})
        assert _infer_domain(wf) == "coordinator"

    def test_orchestrator_por_defecto(self):
        wf = _mk_workflow(uuid4(), action_config={})
        assert _infer_domain(wf) == "orchestrator"

    def test_orchestrator_si_agent_otro(self):
        wf = _mk_workflow(uuid4(), action_config={"agent": "custom"})
        assert _infer_domain(wf) == "orchestrator"

    def test_action_config_None_no_crashea(self):
        wf = _mk_workflow(uuid4(), action_config=None)
        assert _infer_domain(wf) == "orchestrator"


# ── _run_deterministic_step (sync) ───────────────────────────────────────────


class TestRunDeterministicStep:
    def test_sin_tool_marca_error(self):
        step = {"agent": "billing", "params": {}}
        result, prev = _run_deterministic_step(step, 0, "", "tid")
        assert result["success"] is False
        assert "tool" in result["error"].lower()
        assert prev == ""  # prev_output sin cambios

    def test_happy_path(self):
        step = {"agent": "billing", "tool": "list_invoices", "params": {"limit": 5}}
        with patch("app.services.workflow._execution.call_tool", return_value="Encontradas 5 facturas"):
            result, prev = _run_deterministic_step(step, 0, "", "tid-123")
        assert result["success"] is True
        assert result["tool"] == "list_invoices"
        assert result["output"] == "Encontradas 5 facturas"
        assert prev == "Encontradas 5 facturas"

    def test_reemplaza_prev_en_params(self):
        """$prev en params se sustituye por el output anterior."""
        step = {"agent": "billing", "tool": "search_client", "params": {"query": "Cliente $prev"}}
        captured = {}

        def fake_call(tool, params):
            captured.update(params)
            return "ok"

        with patch("app.services.workflow._execution.call_tool", side_effect=fake_call):
            _run_deterministic_step(step, 1, "ACME S.L.", "tid")
        assert captured["query"] == "Cliente ACME S.L."

    def test_inyecta_tenant_id_si_falta(self):
        step = {"agent": "x", "tool": "t", "params": {}}
        captured = {}

        def fake_call(tool, params):
            captured.update(params)
            return ""

        with patch("app.services.workflow._execution.call_tool", side_effect=fake_call):
            _run_deterministic_step(step, 0, "", "tid-XYZ")
        assert captured["tenant_id"] == "tid-XYZ"

    def test_exception_se_captura_en_result(self):
        step = {"agent": "x", "tool": "broken", "params": {}}
        with patch(
            "app.services.workflow._execution.call_tool",
            side_effect=RuntimeError("boom"),
        ):
            result, prev = _run_deterministic_step(step, 0, "previo", "tid")
        assert result["success"] is False
        assert "boom" in result["error"]
        # prev_output NO se modifica en caso de error
        assert prev == "previo"


# ── execute_deterministic_steps (async, mixto) ───────────────────────────────


@pytest.mark.asyncio
class TestExecuteDeterministicSteps:
    async def test_lista_vacia_devuelve_vacio(self):
        results = await execute_deterministic_steps([], "tid", "uid")
        assert results == []

    async def test_steps_deterministicos_secuenciales_propagan_prev(self):
        steps = [
            {"agent": "a", "tool": "t1", "params": {}},
            {"agent": "a", "tool": "t2", "params": {"in": "$prev"}},
        ]
        calls = []

        def fake_call(tool, params):
            calls.append((tool, params.get("in", "")))
            return f"out-{tool}"

        with patch("app.services.workflow._execution.call_tool", side_effect=fake_call):
            results = await execute_deterministic_steps(steps, "tid", "uid")

        assert len(results) == 2
        assert all(r["success"] for r in results)
        # Segundo step recibió output del primero
        assert calls[1] == ("t2", "out-t1")

    async def test_step_sin_tool_pasa_a_reasoning_mockeado(self):
        """Si type='reasoning' o sin 'tool' → reasoning step."""
        steps = [{"agent": "a", "type": "reasoning", "params": {"intent": "hazlo"}}]
        with patch(
            "app.services.workflow._execution._run_reasoning_step",
            new=AsyncMock(return_value=({"agent": "a", "success": True, "type": "reasoning"}, "out")),
        ) as mock_reasoning:
            results = await execute_deterministic_steps(steps, "tid", "uid")
        assert len(results) == 1
        assert results[0]["type"] == "reasoning"
        mock_reasoning.assert_awaited_once()


# ── cancel_execution ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCancelExecution:
    async def _make_wf_exec(self, db, tenant, status="running"):
        wf = Workflow(
            tenant_id=tenant.id, name="t", trigger_type="manual", action_type="prompt"
        )
        db.add(wf)
        await db.commit()
        ex = WorkflowExecution(
            workflow_id=wf.id, tenant_id=tenant.id, status=status,
        )
        db.add(ex)
        await db.commit()
        return wf, ex

    async def test_cancela_ejecucion_running(self, db, _tenant):
        wf, ex = await self._make_wf_exec(db, _tenant, status="running")
        result = await cancel_execution(ex.id, wf.id, _tenant.id, db)
        assert result is not None
        assert result.status == "failed"
        assert "Cancelado" in result.result_log

    async def test_rechaza_si_no_existe(self, db, _tenant):
        # workflow_id válido pero execution_id inventado
        wf, _ = await self._make_wf_exec(db, _tenant)
        result = await cancel_execution(uuid4(), wf.id, _tenant.id, db)
        assert result is None

    async def test_rechaza_si_estado_terminal(self, db, _tenant):
        wf, ex = await self._make_wf_exec(db, _tenant, status="success")
        with pytest.raises(ValueError, match="No se puede cancelar"):
            await cancel_execution(ex.id, wf.id, _tenant.id, db)


# ── run_workflow ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRunWorkflow:
    async def _make_workflow(self, db, tenant, **overrides):
        defaults = dict(
            tenant_id=tenant.id,
            name="WF",
            trigger_type="manual",
            action_type="prompt",
            is_active=True,
            action_config={"instruction": "test"},
            execution_mode="reasoning",
        )
        defaults.update(overrides)
        wf = Workflow(**defaults)
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        return wf

    async def test_lanza_value_error_si_no_existe(self, db, _tenant):
        with pytest.raises(ValueError, match="no encontrado"):
            await run_workflow(uuid4(), _tenant.id, uuid4(), db)

    async def test_lanza_value_error_si_desactivado(self, db, _tenant):
        wf = await self._make_workflow(db, _tenant, is_active=False)
        with pytest.raises(ValueError, match="desactivado"):
            await run_workflow(wf.id, _tenant.id, uuid4(), db)

    async def test_lanza_value_error_si_ya_en_curso(self, db, _tenant):
        wf = await self._make_workflow(db, _tenant)
        # Crear execución en curso
        ex = WorkflowExecution(workflow_id=wf.id, tenant_id=_tenant.id, status="running")
        db.add(ex)
        await db.commit()
        with pytest.raises(ValueError, match="ya tiene una ejecucion"):
            await run_workflow(wf.id, _tenant.id, uuid4(), db)

    async def test_dispatch_reasoning_happy_path(self, db, _tenant):
        wf = await self._make_workflow(db, _tenant)
        with patch(
            "app.services.workflow._execution.dispatch_orchestrator",
            new=AsyncMock(),
        ):
            ex = await run_workflow(wf.id, _tenant.id, uuid4(), db)
        assert ex.status in ("running", "success")
        assert "Tarea IA lanzada" in (ex.result_log or "")
