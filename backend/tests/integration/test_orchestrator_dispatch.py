"""Smoke de integración del path Coordinador → dispatch de agentes.

No es un E2E exhaustivo: verifica que el grafo del orchestrator se ejecuta de
extremo a extremo sin romper el contrato de estado, partiendo de una Task real
en DB. Captura regresiones silenciosas tipo SC-10 (el estado pierde forma entre
nodos, una firma cambia, un import se rompe) que los tests unitarios no ven.

Corre offline: en ENVIRONMENT=testing sin API keys, llm_factory cae a
MockChatModel (ver llm_factory.get_llm), así que no hay llamadas de red.
SMTP saliente se mockea por si el plan clasifica a email.

Gotcha conocido (tasks/lessons): hay que crear una Task REAL en DB antes de
invocar el dispatch, o los inserts dependientes violan la FK task_id.
"""

import asyncio
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.db.base import AsyncSessionLocal
from app.db.models.models import Task, Tenant

_INVOKE_TIMEOUT_S = 90


async def _seed_tenant_and_task(user_intent: str) -> tuple[str, str]:
    """Crea un Tenant + Task en la DB de test y devuelve (tenant_id, task_id)."""
    async with AsyncSessionLocal() as db:
        tenant = Tenant(id=uuid4(), name="Dispatch Test S.L.", nif="B87654321", plan="starter")
        db.add(tenant)
        await db.flush()
        task = Task(
            tenant_id=tenant.id,
            created_by=None,
            status="pending",
            domain="coordinator",
            user_intent=user_intent,
            additional_metadata={"source": "integration_test"},
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return str(tenant.id), str(task.id)


def _initial_state(tenant_id: str, task_id: str, user_intent: str) -> dict:
    """OrchestratorState mínimo (equivalente al _build_initial_state del runtime)."""
    from app.agents.orchestrator import TaskStatus

    return {
        "task_id": task_id,
        "tenant_id": tenant_id,
        "user_id": "",
        "user_intent": user_intent,
        "current_intent": None,
        "classified_domain": None,
        "plan": None,
        "current_step": 0,
        "agent_results": [],
        "status": TaskStatus.PENDING,
        "requires_human_approval": False,
        "approval_id": None,
        "error_message": None,
        "iteration_count": 0,
        "tenant_knowledge": [],
        "additional_metadata": None,
    }


async def _run_dispatch(user_intent: str) -> dict:
    """Siembra DB, fija el contexto de tenant/task e invoca el orchestrator."""
    from app.core.tenant_context import set_current_task, set_current_tenant

    tenant_id, task_id = await _seed_tenant_and_task(user_intent)
    state = _initial_state(tenant_id, task_id, user_intent)
    set_current_tenant(tenant_id)
    set_current_task(task_id)

    async def _fake_send_email(*args, **kwargs):
        return {"success": True, "message_id": "test-fake"}

    with patch("app.services.email.sender.send_email", side_effect=_fake_send_email):
        from app.agents.orchestrator import orchestrator

        final = await asyncio.wait_for(orchestrator.ainvoke(state), timeout=_INVOKE_TIMEOUT_S)

    final["__task_id"] = task_id  # para aserciones
    return final


async def test_orchestrator_dispatch_returns_structured_state():
    """El grafo completa y devuelve el contrato de estado esperado."""
    final = await _run_dispatch(
        "Crea un cliente llamado Acme Test con email acme@test.com"
    )

    assert isinstance(final, dict)
    # Contrato núcleo del OrchestratorState tras correr el grafo.
    assert "status" in final
    assert final.get("task_id") == final["__task_id"]
    assert isinstance(final.get("agent_results"), list)
    # El plan, si existe, es una lista (puede ser None/[] si clasifica a chat).
    assert final.get("plan") is None or isinstance(final.get("plan"), list)


async def test_dispatch_results_follow_agentresult_contract():
    """Cada resultado de agente respeta la forma de AgentResult (agent/success)."""
    final = await _run_dispatch(
        "Emite una factura de 100 euros + IVA al cliente Acme Test"
    )

    for result in final.get("agent_results") or []:
        assert "agent" in result, f"AgentResult sin 'agent': {result}"
        assert "success" in result, f"AgentResult sin 'success': {result}"


async def test_dispatch_does_not_leave_task_pending_without_trace():
    """Tras el dispatch, el estado refleja un desenlace (no queda en PENDING mudo)."""
    from app.agents.orchestrator import TaskStatus

    final = await _run_dispatch("Dame el resumen contable del mes pasado")

    status = final.get("status")
    status_str = status.value if hasattr(status, "value") else str(status)
    # Debe haber avanzado: o terminó, o falló con mensaje, o pidió aprobación.
    progressed = (
        status != TaskStatus.PENDING
        or final.get("error_message")
        or final.get("requires_human_approval")
        or final.get("classified_domain") is not None
    )
    assert progressed, f"El orchestrator no avanzó desde PENDING: {final!r}"
