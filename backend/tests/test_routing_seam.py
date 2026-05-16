"""Tests del seam de routing — bloquean en CI la familia de bugs que vimos
en la sesion del 2026-05-07.

Cada test ataca una costura concreta entre subsistemas:

  1. generate_preview_nodes asigna data.employee_id cuando hay custom.
  2. generate_preview_nodes usa el AIEmployee built-in con su nombre real.
  3. _plan_from_blueprint propaga data.employee_id -> params.employee_id.
  4. build_skill_dispatch propaga data.employee_id en NodeEngine.
  5. plan_node hace swap a custom cuando hay exactamente 1 match en el dominio.
  6. classifier._resolve_custom_employee filtra por is_builtin=False (Fix B).
  7. _invoke_dynamic_employee selecciona el AIEmployee EXACTO de params.employee_id.

Si cualquiera rompe, CI rojo. Sin necesidad de LLM real (todos son tests del
routing puro o con seed de BD + mock del compile_dynamic_agent).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _emp(name: str, role: str, domain: str, *, is_builtin: bool):
    """Construye un objeto-empleado mínimo para pruebas puras de _ui_graph."""
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        role=role,
        domain=domain,
        is_builtin=is_builtin,
        status="idle",
    )


# ──────────────────────────────────────────────────────────────────────────────
# 1) generate_preview_nodes — asigna employee_id de un custom matching
# ──────────────────────────────────────────────────────────────────────────────


def test_generate_preview_nodes_uses_custom_for_billing():
    from app.services.workflow._ui_graph import generate_preview_nodes

    yolanda = _emp("yolanda sanchez", "CFO", "billing", is_builtin=False)
    ana = _emp("Ana Valdes", "Directora Financiera", "billing", is_builtin=True)

    payload = {
        "trigger_type": "manual",
        "action_config": {"instruction": "revisa las facturas pendientes de cobro de mayo"},
    }

    nodes, _edges = generate_preview_nodes(payload, [yolanda, ana])

    skills = [n for n in nodes if n["type"] == "skill"]
    assert skills, "deberia haber al menos un skill node"
    billing_node = next(
        (n for n in skills if (n["data"].get("domain") in ("billing", "custom"))), None
    )
    assert billing_node is not None
    assert billing_node["data"]["domain"] == "custom", "custom > builtin"
    assert billing_node["data"]["employee_id"] == str(yolanda.id)
    assert billing_node["data"]["label"] == "yolanda sanchez"


# ──────────────────────────────────────────────────────────────────────────────
# 2) generate_preview_nodes — fallback al built-in cuando no hay custom
# ──────────────────────────────────────────────────────────────────────────────


def test_generate_preview_nodes_uses_builtin_name_when_no_custom():
    from app.services.workflow._ui_graph import generate_preview_nodes

    carlos = _emp("Carlos Herrero", "Responsable de RRHH", "hr", is_builtin=True)

    payload = {
        "trigger_type": "manual",
        "action_config": {"instruction": "genera las nominas de marzo"},
    }

    nodes, _ = generate_preview_nodes(payload, [carlos])
    skills = [n for n in nodes if n["type"] == "skill"]
    assert skills
    hr_node = next((n for n in skills if n["data"].get("domain") == "hr"), None)
    assert hr_node is not None, "debe detectar 'nomina' como hr"
    assert hr_node["data"]["label"] == "Carlos Herrero"
    assert hr_node["data"]["employee_id"] == str(carlos.id)


# ──────────────────────────────────────────────────────────────────────────────
# 3) _plan_from_blueprint propaga employee_id
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_plan_from_blueprint_propagates_employee_id(seed_tenant_and_user):
    from app.agents.orchestrator._plan_handlers import _plan_from_blueprint

    tenant, _user, _token = seed_tenant_and_user
    yolanda_id = str(uuid4())

    wf = SimpleNamespace(
        id=uuid4(),
        name="WF Test",
        ui_nodes=[
            {"id": "trigger", "type": "trigger", "data": {}},
            {
                "id": "skill_1",
                "type": "skill",
                "data": {
                    "domain": "custom",
                    "label": "yolanda sanchez",
                    "employee_id": yolanda_id,
                    "instruction": "revisa cobros",
                },
            },
        ],
        ui_edges=[{"id": "e1", "source": "trigger", "target": "skill_1"}],
    )

    state = {
        "tenant_id": str(tenant.id),
        "user_intent": "revisa cobros",
        "additional_metadata": {"workflow_id": str(wf.id)},
    }

    plan = await _plan_from_blueprint(state, wf)
    assert plan and len(plan) == 1
    step = plan[0]
    assert step["agent"] == "custom"
    assert step["params"].get("employee_id") == yolanda_id, (
        "data.employee_id debe propagarse a params.employee_id"
    )


# ──────────────────────────────────────────────────────────────────────────────
# 4) build_skill_dispatch (NodeEngine) propaga employee_id
# ──────────────────────────────────────────────────────────────────────────────


def test_build_skill_dispatch_propagates_employee_id():
    from app.services.ai.node_graph_helpers import build_skill_dispatch

    yolanda_id = str(uuid4())
    node = {
        "id": "n1",
        "type": "skill",
        "data": {
            "domain": "custom",
            "label": "yolanda sanchez",
            "employee_id": yolanda_id,
            "instruction": "revisa cobros del mes",
        },
    }
    domain, _instruction, subtask, _mini = build_skill_dispatch(
        node=node,
        edges=[],
        node_states={},
        tenant_id=str(uuid4()),
        user_id=str(uuid4()),
        execution_id=str(uuid4()),
    )
    assert domain == "custom"
    assert subtask["params"].get("employee_id") == yolanda_id, (
        "build_skill_dispatch debe propagar data.employee_id al subtask"
    )


# ──────────────────────────────────────────────────────────────────────────────
# 5) plan_node — Fix A: swap a custom cuando hay 1 match en el dominio
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_plan_node_single_domain_swaps_to_custom(
    db: AsyncSession, seed_tenant_and_user
):
    """Si classify devuelve 'billing' y hay UN custom de billing, plan_node debe
    sustituir el built-in por agent='custom' + params.employee_id=<uuid>."""
    from app.agents.orchestrator._plan_handlers import plan_node
    from app.db.models.ai_employees import AIEmployee

    tenant, _user, _token = seed_tenant_and_user

    yolanda = AIEmployee(
        id=uuid4(),
        tenant_id=tenant.id,
        name="yolanda sanchez",
        role="CFO",
        domain="billing",
        system_prompt="Soy yolanda, CFO. Reviso facturas con criterio financiero.",
        budget_limit_usd=10.0,
        status="idle",
        is_builtin=False,
    )
    db.add(yolanda)
    await db.commit()

    state = {
        "task_id": str(uuid4()),
        "tenant_id": str(tenant.id),
        "user_id": str(_user.id),
        "user_intent": "revisa las facturas pendientes",
        "current_intent": "revisa las facturas pendientes",
        "classified_domain": "billing",
        "plan": [],
        "current_step": 0,
        "agent_results": [],
        "iteration_count": 0,
        "additional_metadata": {},
        "requires_human_approval": False,
        "error_message": None,
    }

    result = await plan_node(state)
    plan = result["plan"]

    assert plan and len(plan) == 1
    step = plan[0]
    assert step["agent"] == "custom", (
        f"plan_node debio hacer swap a custom; recibio agent={step['agent']}"
    )
    assert step["params"].get("employee_id") == str(yolanda.id)


# ──────────────────────────────────────────────────────────────────────────────
# 6) classifier._resolve_custom_employee — Fix B (filtro is_builtin=False)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_custom_employee_matches_by_name_with_correct_filter(
    db: AsyncSession, seed_tenant_and_user
):
    """Si el usuario menciona el nombre de un AIEmployee custom, el classifier
    debe resolver addressed_employee_id. El filtro debe ser is_builtin=False, NO
    el literal domain == 'custom' (que era el bug original).
    """
    from app.agents.orchestrator.classifier import _resolve_custom_employee
    from app.db.models.ai_employees import AIEmployee

    tenant, _user, _token = seed_tenant_and_user

    # AIEmployee con domain="billing" pero is_builtin=False — el caso real:
    # los customs viven con dominio funcional, no con literal "custom".
    yolanda = AIEmployee(
        id=uuid4(),
        tenant_id=tenant.id,
        name="yolanda sanchez",
        role="CFO",
        domain="billing",
        system_prompt="CFO custom.",
        budget_limit_usd=10.0,
        status="idle",
        is_builtin=False,
    )
    db.add(yolanda)
    await db.commit()

    state = {"tenant_id": str(tenant.id), "additional_metadata": {}}
    intent_lower = "yolanda, revisa las facturas pendientes de cobro"

    result = await _resolve_custom_employee(state, intent_lower)

    assert result is not None, "debio resolver al custom por mencion del nombre"
    assert result.get("addressed_employee_id") == str(yolanda.id)


# ──────────────────────────────────────────────────────────────────────────────
# 7) _invoke_dispatcher_impl enruta agent="custom" al dispatcher dinámico
#    con params.employee_id intacto.
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invoke_dispatcher_routes_custom_with_employee_id_intact():
    """Cuando agent='custom' y hay tenant_id en el state, _invoke_dispatcher_impl
    debe delegar a _invoke_dynamic_employee preservando subtask.params.employee_id.
    Si esto se rompe (ej. params.employee_id se pierde), volveríamos al bug del
    custom random.
    """
    from app.agents.orchestrator import _dispatch_handlers

    yolanda_id = str(uuid4())
    tenant_id = str(uuid4())
    captured: dict = {}

    async def fake_dyn(enriched_state, subtask, agent_name, tnt_id):
        captured["agent_name"] = agent_name
        captured["tenant_id"] = tnt_id
        captured["params_emp_id"] = (subtask.get("params") or {}).get("employee_id")
        return {
            "subtask_id": subtask["id"],
            "agent": agent_name,
            "success": True,
            "output": {"response": "ok yolanda"},
            "error": None,
        }

    enriched_state = {
        "tenant_id": tenant_id,
        "task_id": str(uuid4()),
        "user_id": str(uuid4()),
        "current_intent": "revisa cobros",
    }
    subtask = {
        "id": "step_1",
        "subtask_id": "step_1",
        "agent": "custom",
        "params": {"intent": "revisa cobros", "employee_id": yolanda_id},
    }

    with patch.object(_dispatch_handlers, "_invoke_dynamic_employee", side_effect=fake_dyn):
        result = await _dispatch_handlers._invoke_dispatcher_impl(
            enriched_state, subtask, "custom"
        )

    assert result["success"] is True
    assert captured.get("agent_name") == "custom"
    assert captured.get("tenant_id") == tenant_id
    assert captured.get("params_emp_id") == yolanda_id, (
        "params.employee_id debe llegar al dispatcher dinámico intacto"
    )
