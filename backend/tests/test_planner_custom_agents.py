"""Tests para el soporte de AIEmployees custom en el planner del orchestrator.

Verifica end-to-end que cualquier AIEmployee con is_builtin=False creado
por el usuario aparezca como opción en el plan multi-step generado:

  1. _load_tenant_custom_employees lee solo custom + idle/working
  2. _custom_employees_block construye el texto inyectado al prompt
  3. _custom_employees_hash es estable y discrimina cambios
  4. _plan_from_llm propaga employee_id del LLM al SubTask params
  5. validate_node falla si agent='custom' sin employee_id ni addressed_id
  6. validate_node pasa si agent='custom' con employee_id en params
  7. _invoke_dynamic_employee usa params.employee_id antes que metadata
  8. _invoke_dynamic_employee propaga mensaje útil cuando hay TimeoutError
     o cualquier excepción sin str() (antes producía error="")
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


# ─── Helpers de planner ──────────────────────────────────────────────────────


class TestCustomEmployeesHelpers:
    @pytest.mark.asyncio
    async def test_load_returns_only_custom_active(
        self, db: AsyncSession, seed_tenant_and_user
    ):
        from app.agents.orchestrator._plan_handlers import (
            _load_tenant_custom_employees,
        )
        from app.db.models.ai_employees import AIEmployee

        tenant, _user, _token = seed_tenant_and_user

        builtin = AIEmployee(
            id=uuid4(), tenant_id=tenant.id, name="Ana Builtin", role="Director",
            domain="billing", is_builtin=True, status="idle",
            system_prompt="...", icon="x", avatar_color="#fff",
        )
        custom_active = AIEmployee(
            id=uuid4(), tenant_id=tenant.id, name="CTO Custom", role="CTO",
            domain="custom", is_builtin=False, status="idle",
            system_prompt="...", icon="x", avatar_color="#fff",
        )
        custom_inactive = AIEmployee(
            id=uuid4(), tenant_id=tenant.id, name="Otro Custom", role="Asesor",
            domain="custom", is_builtin=False, status="archived",
            system_prompt="...", icon="x", avatar_color="#fff",
        )
        db.add_all([builtin, custom_active, custom_inactive])
        await db.commit()

        result = await _load_tenant_custom_employees(str(tenant.id))
        names = [e.name for e in result]
        assert names == ["CTO Custom"]  # solo custom + activo

    def test_block_text_contains_name_role_id(self):
        from app.agents.orchestrator._plan_handlers import _custom_employees_block

        emp = MagicMock()
        emp.name = "Marcos Recio"
        emp.role = "CTO"
        emp.id = "abc-123"
        emp.system_prompt = "Soy el CTO. Coordino tecnología."
        block = _custom_employees_block([emp])
        assert "Marcos Recio" in block
        assert "CTO" in block
        assert "abc-123" in block
        assert 'agent="custom"' in block

    def test_block_includes_expertise_snippet_and_use_guidance(self):
        from app.agents.orchestrator._plan_handlers import _custom_employees_block

        emp = MagicMock()
        emp.name = "Eva Auditora"
        emp.role = "Auditora Interna"
        emp.id = "xyz-789"
        emp.system_prompt = (
            "Soy Eva, auditora interna. Reviso flujos de gastos, identifico "
            "duplicados y compruebo cumplimiento de la política interna."
        )
        block = _custom_employees_block([emp])
        # El snippet del expertise debe aparecer para que el LLM pueda juzgar
        assert "auditora interna" in block.lower()
        assert "duplicados" in block
        # La nueva guía debe permitir asignación sin mención explícita
        assert "AUNQUE" in block  # marca la frase clave del prompt
        # Y debe distinguir uso vs builtin
        assert "PRECEDENCIA" in block

    def test_block_empty_when_no_employees(self):
        from app.agents.orchestrator._plan_handlers import _custom_employees_block

        assert _custom_employees_block([]) == ""

    def test_hash_stable_and_changes_with_set(self):
        from app.agents.orchestrator._plan_handlers import _custom_employees_hash

        e1, e2 = MagicMock(), MagicMock()
        e1.id, e1.name, e1.role = "id-1", "Ana", "CFO"
        e2.id, e2.name, e2.role = "id-2", "Bea", "CTO"

        h_just_e1 = _custom_employees_hash([e1])
        h_e1_e2 = _custom_employees_hash([e1, e2])
        h_again = _custom_employees_hash([e1])

        assert h_just_e1 == h_again
        assert h_just_e1 != h_e1_e2
        assert _custom_employees_hash([]) == "no-custom"


# ─── validate_node: custom + employee_id ─────────────────────────────────────


class TestValidateNodeCustomAgent:
    @pytest.mark.asyncio
    async def test_custom_with_params_employee_id_passes(self):
        from app.agents.orchestrator._validate_handlers import validate_node
        from app.agents.orchestrator.state import TaskStatus

        emp_id = str(uuid4())
        state = {
            "user_intent": "Marcos prepárame el resumen",
            "plan": [
                {"id": "step_1", "agent": "custom", "action": "process",
                 "params": {"intent": "Resumen", "employee_id": emp_id},
                 "depends_on": [], "status": "pending"}
            ],
            "iteration_count": 0,
            "tenant_id": "00000000-0000-0000-0000-000000000001",
        }
        result = await validate_node(state)
        assert result["status"] == TaskStatus.EXECUTING

    @pytest.mark.asyncio
    async def test_custom_with_addressed_employee_id_in_metadata_passes(self):
        from app.agents.orchestrator._validate_handlers import validate_node
        from app.agents.orchestrator.state import TaskStatus

        emp_id = str(uuid4())
        state = {
            "user_intent": "Marcos prepárame el resumen",
            "plan": [
                {"id": "step_1", "agent": "custom", "action": "process",
                 "params": {"intent": "Resumen"},
                 "depends_on": [], "status": "pending"}
            ],
            "iteration_count": 0,
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "additional_metadata": {"addressed_employee_id": emp_id},
        }
        result = await validate_node(state)
        assert result["status"] == TaskStatus.EXECUTING

    @pytest.mark.asyncio
    async def test_custom_without_employee_id_anywhere_fails(self):
        from app.agents.orchestrator._validate_handlers import validate_node
        from app.agents.orchestrator.state import TaskStatus

        state = {
            "user_intent": "haz algo",
            "plan": [
                {"id": "step_1", "agent": "custom", "action": "process",
                 "params": {"intent": "?"},
                 "depends_on": [], "status": "pending"}
            ],
            "iteration_count": 0,
            "tenant_id": "00000000-0000-0000-0000-000000000001",
        }
        result = await validate_node(state)
        assert result["status"] == TaskStatus.FAILED
        assert "employee_id" in result["error_message"]


# ─── _invoke_dynamic_employee: per-step employee_id prioritario ──────────────


class TestDispatcherCustomPerStepEmployee:
    @pytest.mark.asyncio
    async def test_step_params_employee_id_wins_over_metadata(
        self, db: AsyncSession, seed_tenant_and_user
    ):
        """Si el subtask trae employee_id en params, usa ese — no el global."""
        from app.agents.orchestrator._dispatch_handlers import _invoke_dynamic_employee
        from app.db.models.ai_employees import AIEmployee

        tenant, _user, _token = seed_tenant_and_user

        # Dos custom employees: el del state.metadata vs el del step.params.
        # Esperamos que se invoque el del step.params.
        global_emp = AIEmployee(
            id=uuid4(), tenant_id=tenant.id, name="Global CTO", role="CTO",
            domain="custom", is_builtin=False, status="idle",
            system_prompt="prompt global", icon="x", avatar_color="#fff",
        )
        per_step_emp = AIEmployee(
            id=uuid4(), tenant_id=tenant.id, name="Step CFO", role="CFO",
            domain="custom", is_builtin=False, status="idle",
            system_prompt="prompt per-step", icon="x", avatar_color="#fff",
        )
        db.add_all([global_emp, per_step_emp])
        await db.commit()

        captured: dict = {}

        async def fake_compile(employee_id: str, _db):
            captured["employee_id"] = employee_id
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(return_value={
                "messages": [],
                "agent_results": [{"action_taken": "ok"}],
                "status": "done",
            })
            return mock_graph

        async def fake_budget(*_a, **_kw):
            return True

        with patch(
            "app.agents.workers.compile_dynamic_agent", new=fake_compile
        ), patch(
            "app.agents.workers.check_agent_budget", new=fake_budget
        ):
            await _invoke_dynamic_employee(
                enriched_state={
                    "tenant_id": str(tenant.id),
                    "user_intent": "...",
                    "additional_metadata": {
                        "addressed_employee_id": str(global_emp.id),
                    },
                },
                subtask={
                    "id": "step_1",
                    "params": {
                        "intent": "Pregunta al CFO",
                        "employee_id": str(per_step_emp.id),
                    },
                },
                agent_name="custom",
                tenant_id=str(tenant.id),
            )

        assert captured["employee_id"] == str(per_step_emp.id)


# ─── Bug fix: error vacío cuando hay TimeoutError ────────────────────────────


class TestDispatcherErrorPropagation:
    @pytest.mark.asyncio
    async def test_timeout_error_propagates_meaningful_message(
        self, db: AsyncSession, seed_tenant_and_user
    ):
        """asyncio.TimeoutError().__str__() devuelve '' por defecto. El
        dispatcher debe detectarlo y dar al usuario un mensaje claro
        ("Timeout de 120s al ejecutar..."), no propagar error=''.
        """
        from app.agents.orchestrator._dispatch_handlers import _invoke_dynamic_employee
        from app.db.models.ai_employees import AIEmployee

        tenant, _user, _token = seed_tenant_and_user

        emp = AIEmployee(
            id=uuid4(), tenant_id=tenant.id, name="Slow CEO", role="CEO",
            domain="custom", is_builtin=False, status="idle",
            system_prompt="prompt muy largo", icon="x", avatar_color="#fff",
        )
        db.add(emp)
        await db.commit()

        async def fake_compile(_emp_id, _db):
            mock = MagicMock()
            # Simulamos un grafo que tarda demasiado: ainvoke nunca completa.
            # asyncio.wait_for lo cancelará y lanzará TimeoutError.
            async def _hangs(*_a, **_kw):
                await asyncio.sleep(999)
            mock.ainvoke = _hangs
            return mock

        async def fake_budget(*_a, **_kw):
            return True

        # Bajamos timeout a 0.1s con monkeypatch para no esperar 120s reales.
        with patch(
            "app.agents.workers.compile_dynamic_agent", new=fake_compile
        ), patch(
            "app.agents.workers.check_agent_budget", new=fake_budget
        ), patch(
            "app.agents.orchestrator._dispatch_handlers.asyncio.wait_for",
            new=AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            result = await _invoke_dynamic_employee(
                enriched_state={
                    "tenant_id": str(tenant.id),
                    "user_intent": "lo que sea",
                    "additional_metadata": {},
                },
                subtask={
                    "id": "step_x",
                    "params": {"intent": "test", "employee_id": str(emp.id)},
                },
                agent_name="custom",
                tenant_id=str(tenant.id),
            )

        assert result is not None
        assert result["success"] is False
        assert result["error"], "error must not be empty"
        assert "Timeout" in result["error"]
        assert "Slow CEO" in result["error"]

    @pytest.mark.asyncio
    async def test_exception_without_message_falls_back_to_type_name(
        self, db: AsyncSession, seed_tenant_and_user
    ):
        """Cualquier excepción con str() vacío debe propagar el tipo."""
        from app.agents.orchestrator._dispatch_handlers import _invoke_dynamic_employee
        from app.db.models.ai_employees import AIEmployee

        tenant, _user, _token = seed_tenant_and_user

        emp = AIEmployee(
            id=uuid4(), tenant_id=tenant.id, name="Crashy Custom", role="X",
            domain="custom", is_builtin=False, status="idle",
            system_prompt="x", icon="x", avatar_color="#fff",
        )
        db.add(emp)
        await db.commit()

        class _Mystery(Exception):
            pass

        async def fake_compile(*_a, **_kw):
            raise _Mystery()  # str(_Mystery()) == ''

        async def fake_budget(*_a, **_kw):
            return True

        with patch(
            "app.agents.workers.compile_dynamic_agent", new=fake_compile
        ), patch(
            "app.agents.workers.check_agent_budget", new=fake_budget
        ):
            result = await _invoke_dynamic_employee(
                enriched_state={
                    "tenant_id": str(tenant.id),
                    "user_intent": "x",
                    "additional_metadata": {},
                },
                subtask={
                    "id": "step_x",
                    "params": {"employee_id": str(emp.id)},
                },
                agent_name="custom",
                tenant_id=str(tenant.id),
            )

        assert result is not None
        assert result["success"] is False
        assert result["error"], "error must not be empty"
        assert "_Mystery" in result["error"] or "sin mensaje" in result["error"]
