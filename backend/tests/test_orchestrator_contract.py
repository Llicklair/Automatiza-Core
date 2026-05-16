"""QA.CTR — tests de contrato JSON orquestador ↔ agente.

El orquestador y los agentes se comunican a través de dos estructuras
canónicas definidas en `agents/orchestrator/state.py`:

  - `AgentResult` TypedDict: lo que cada subtarea devuelve al orchestrator
  - `OrchestratorState` TypedDict: estado compartido del grafo LangGraph

Estos tests blindan ese contrato:
  1. Las keys obligatorias existen y tienen el tipo declarado.
  2. JSON round-trip no pierde campos.
  3. Cada agent package expone los símbolos públicos esperados.

Si un agente o el orchestrator añade/quita campos, este test falla y
exige actualización explícita (visible en code review).
"""
from __future__ import annotations

import importlib
import json
from typing import get_type_hints

import pytest
from app.agents.orchestrator.state import AgentResult, OrchestratorState

# Schema canónico — congelado en este test. Cambiar AgentResult o
# OrchestratorState exige actualizar este test y revisar en PR.
EXPECTED_AGENT_RESULT_FIELDS: frozenset[str] = frozenset({
    "subtask_id",
    "agent",
    "success",
    "output",
    "error",
})


# Agentes esperados del MVP — cada paquete debe importarse sin fallo y
# exportar al menos `graph` o `workflow` (entry point LangGraph).
EXPECTED_AGENTS: tuple[str, ...] = (
    "billing",
    "accounting",
    "banking",
    "crm",
    "hr",
    "marketing",
    "recruitment",
    "documents",
    "email",
    "rag",
    "validators",
    "compliance",
    "excel",
    "uploads",
    "orchestrator",
)


class TestAgentResultContract:
    def test_keys_canonicas(self):
        hints = get_type_hints(AgentResult)
        assert frozenset(hints.keys()) == EXPECTED_AGENT_RESULT_FIELDS, (
            f"AgentResult shape cambió: faltan {EXPECTED_AGENT_RESULT_FIELDS - set(hints)} "
            f"o sobran {set(hints) - EXPECTED_AGENT_RESULT_FIELDS}"
        )

    def test_construir_y_serializar_a_json(self):
        sample: AgentResult = {
            "subtask_id": "sub-1",
            "agent": "billing",
            "success": True,
            "output": {"invoice_id": "abc", "number": "A2026-0001"},
            "error": None,
        }
        # Round-trip JSON: el contrato debe ser serializable sin custom encoder.
        s = json.dumps(sample)
        restored = json.loads(s)
        assert restored["subtask_id"] == "sub-1"
        assert restored["success"] is True
        assert restored["output"]["invoice_id"] == "abc"
        assert restored["error"] is None

    def test_error_path(self):
        """Si un agente falla, success=False y error contiene mensaje."""
        sample: AgentResult = {
            "subtask_id": "sub-1",
            "agent": "billing",
            "success": False,
            "output": None,
            "error": "Cliente no encontrado",
        }
        s = json.dumps(sample)
        restored = json.loads(s)
        assert restored["success"] is False
        assert "no encontrado" in restored["error"]


class TestOrchestratorState:
    def test_state_tiene_campos_minimos(self):
        hints = get_type_hints(OrchestratorState)
        # Estos campos son los que dispatchers/handlers asumen presentes.
        required = {"task_id", "tenant_id", "user_id", "user_intent"}
        missing = required - set(hints.keys())
        assert not missing, f"OrchestratorState pierde campos críticos: {missing}"


class TestAgentPackageExports:
    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS)
    def test_agent_module_importable(self, agent_name: str):
        """Cada paquete de agente declarado en MVP debe importarse sin error."""
        mod = importlib.import_module(f"app.agents.{agent_name}")
        assert mod is not None

    @pytest.mark.parametrize(
        "agent_name",
        # Sub-set: agentes que sí construyen grafo LangGraph (no helpers).
        ("billing", "accounting", "banking", "hr", "recruitment", "marketing"),
    )
    def test_agent_exporta_graph_o_workflow(self, agent_name: str):
        """Cada agent ejecutable debe exponer `graph` (o `workflow`)."""
        mod = importlib.import_module(f"app.agents.{agent_name}")
        has_entry = hasattr(mod, "graph") or hasattr(mod, "workflow")
        assert has_entry, (
            f"app.agents.{agent_name} no exporta `graph` ni `workflow`. "
            "El orquestador asume al menos uno como entry point."
        )


class TestJsonSerializationSafety:
    def test_output_acepta_tipos_jsonables(self):
        """`output: Any` en el contrato — debe aceptar primitivos + dict + list."""
        for value in (
            None,
            "string",
            42,
            3.14,
            True,
            [1, 2, 3],
            {"nested": {"a": 1}},
        ):
            sample: AgentResult = {
                "subtask_id": "x", "agent": "test",
                "success": True, "output": value, "error": None,
            }
            json.dumps(sample)  # no debe raisear

    def test_falla_visible_si_output_no_serializa(self):
        """Si output incluye un tipo no JSON, el contrato lo expone al caller."""
        class NotJson:
            pass
        sample = {
            "subtask_id": "x", "agent": "test",
            "success": True, "output": NotJson(), "error": None,
        }
        with pytest.raises(TypeError):
            json.dumps(sample)
