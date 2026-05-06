"""Tests para los dos fixes del planner robustness:

1. claude_code.with_structured_output: parser raw_decode tolerante a prosa
   alrededor del JSON, comillas en código markdown, JSONs sibling, etc.

2. _validate_handlers.validate_node: fallback heurístico cuando el LLM
   devuelve plan vacío — clasifica por keywords y delega a 1 agente
   en vez de marcar la tarea como FAILED.
"""
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, Field


# ─── Fix B: claude_code parser ───────────────────────────────────────────────


class _PlanStep(BaseModel):
    agent: str
    action: str = "process"


class _Plan(BaseModel):
    steps: list[_PlanStep] = Field(default_factory=list)


def _parse_via_claude_code(raw: str):
    """Invoca el parser interno de ClaudeCodeChatModel.with_structured_output."""
    from app.core.llm.claude_code import ClaudeCodeChatModel

    model = ClaudeCodeChatModel()
    runnable = model.with_structured_output(_Plan, method="json_mode")
    # El parser real está dentro del closure _parse. Reconstruimos sintetizando
    # un _generate sin invocar el subprocess: monkeypatch _generate.
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult

    def fake_generate(messages, stop=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=raw))])

    model._generate = fake_generate  # type: ignore[method-assign]
    return runnable.invoke("dummy")


class TestClaudeCodeStructuredOutputParser:
    def test_clean_json(self):
        plan = _parse_via_claude_code('{"steps": [{"agent": "billing"}]}')
        assert isinstance(plan, _Plan)
        assert len(plan.steps) == 1
        assert plan.steps[0].agent == "billing"

    def test_json_wrapped_in_markdown(self):
        raw = '```json\n{"steps": [{"agent": "hr"}]}\n```'
        plan = _parse_via_claude_code(raw)
        assert plan.steps[0].agent == "hr"

    def test_json_with_prose_before(self):
        # Caso real: Claude Code añade explicación antes del JSON.
        raw = (
            "Claro, descompongo la tarea. Aquí tienes el plan:\n\n"
            '{"steps": [{"agent": "banking", "action": "check_balances"}]}'
        )
        plan = _parse_via_claude_code(raw)
        assert plan.steps[0].agent == "banking"

    def test_json_with_prose_after(self):
        raw = '{"steps": [{"agent": "compliance"}]}\n\nEspero que esto te sirva.'
        plan = _parse_via_claude_code(raw)
        assert plan.steps[0].agent == "compliance"

    def test_two_sibling_objects_takes_first(self):
        # Antes el regex greedy `{.*}` capturaba desde el primer `{` hasta
        # el último `}` y fallaba al parsear este caso.
        raw = '{"steps": [{"agent": "billing"}]}\n\n{"otro": "objeto"}'
        plan = _parse_via_claude_code(raw)
        assert plan.steps[0].agent == "billing"

    def test_brace_in_prose_then_real_json(self):
        # Texto con `{` literales no parseables seguido del JSON real.
        raw = "Plan: {algo no JSON} pero el plan es:\n" '{"steps": [{"agent": "crm"}]}'
        plan = _parse_via_claude_code(raw)
        assert plan.steps[0].agent == "crm"


# ─── Fix A: validate_node fallback heurístico ────────────────────────────────


class TestValidateNodeHeuristicFallback:
    @pytest.mark.asyncio
    async def test_empty_plan_with_billing_keywords_routes_to_billing(self):
        from app.agents.orchestrator._validate_handlers import validate_node
        from app.agents.orchestrator.state import TaskStatus

        state = {
            "user_intent": "Lista las facturas pendientes de cobro de este mes",
            "plan": [],
            "iteration_count": 0,
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "classified_domain": "coordinator",
        }
        result = await validate_node(state)
        assert result["status"] == TaskStatus.EXECUTING
        assert len(result["plan"]) == 1
        assert result["plan"][0]["agent"] == "billing"
        assert result["plan"][0]["params"]["intent"] == state["user_intent"]

    @pytest.mark.asyncio
    async def test_empty_plan_with_payroll_keywords_routes_to_hr(self):
        from app.agents.orchestrator._validate_handlers import validate_node
        from app.agents.orchestrator.state import TaskStatus

        state = {
            "user_intent": "Genera todas las nóminas de los empleados activos",
            "plan": [],
            "iteration_count": 0,
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "classified_domain": "coordinator",
        }
        result = await validate_node(state)
        assert result["status"] == TaskStatus.EXECUTING
        assert result["plan"][0]["agent"] == "hr"

    @pytest.mark.asyncio
    async def test_empty_plan_with_no_keywords_falls_back_to_chat(self):
        from app.agents.orchestrator._validate_handlers import validate_node
        from app.agents.orchestrator.state import TaskStatus

        state = {
            "user_intent": "hola",  # texto sin keywords reconocidas
            "plan": [],
            "iteration_count": 0,
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "classified_domain": "coordinator",
        }
        result = await validate_node(state)
        # 'chat' está en VALID_DOMAINS → fallback exitoso a chat
        assert result["status"] == TaskStatus.EXECUTING
        assert result["plan"][0]["agent"] == "chat"

    @pytest.mark.asyncio
    async def test_non_empty_plan_passes_through(self):
        from app.agents.orchestrator._validate_handlers import validate_node
        from app.agents.orchestrator.state import TaskStatus

        state = {
            "user_intent": "anything",
            "plan": [
                {"id": "step_1", "agent": "billing", "action": "process",
                 "params": {}, "depends_on": [], "status": "pending"}
            ],
            "iteration_count": 0,
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "classified_domain": "coordinator",
        }
        result = await validate_node(state)
        assert result["status"] == TaskStatus.EXECUTING
        assert len(result["plan"]) == 1
        assert result["plan"][0]["agent"] == "billing"

    @pytest.mark.asyncio
    async def test_invalid_agent_in_plan_still_fails(self):
        from app.agents.orchestrator._validate_handlers import validate_node
        from app.agents.orchestrator.state import TaskStatus

        state = {
            "user_intent": "anything",
            "plan": [
                {"id": "step_1", "agent": "nonexistent_agent", "action": "process",
                 "params": {}, "depends_on": [], "status": "pending"}
            ],
            "iteration_count": 0,
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "classified_domain": "coordinator",
        }
        result = await validate_node(state)
        assert result["status"] == TaskStatus.FAILED
