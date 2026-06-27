"""Guard de idempotencia para POST /api/v1/workflows/{id}/run-with-context.

run_workflow_with_context debe rechazar (igual que run_workflow) cuando el
workflow ya tiene una ejecucion activa (running/pending) -> 409. Sin ejecucion
activa NO debe dar 409.
"""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


async def _make_workflow(db, tenant):
    from app.db.models.models import Workflow

    wf = Workflow(
        tenant_id=tenant.id,
        name="WF ctx",
        trigger_type="manual",
        action_type="prompt",
        is_active=True,
        action_config={"instruction": "test"},
        execution_mode="reasoning",
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return wf


@pytest.mark.asyncio
async def test_run_with_context_rechaza_si_ya_activa(
    auth_client: AsyncClient, seed_tenant_and_user, db
):
    """NEGATIVO: con una ejecucion running ya existente -> 409 (no crea 2a)."""
    from app.db.models.models import WorkflowExecution

    tenant, _, _ = seed_tenant_and_user
    wf = await _make_workflow(db, tenant)

    ex = WorkflowExecution(workflow_id=wf.id, tenant_id=tenant.id, status="running")
    db.add(ex)
    await db.commit()

    resp = await auth_client.post(
        f"/api/v1/workflows/{wf.id}/run-with-context",
        json={"context": "extra"},
    )
    assert resp.status_code == 409
    assert "en curso" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_run_with_context_sin_activa_no_es_409(
    auth_client: AsyncClient, seed_tenant_and_user, db
):
    """CONTROL: sin ejecucion activa NO debe dar 409.

    Se mockea dispatch_orchestrator (lo dispara _dispatch_reasoning) para no
    ejecutar el orquestador real.
    """
    tenant, _, _ = seed_tenant_and_user
    wf = await _make_workflow(db, tenant)

    with patch(
        "app.services.workflow._execution.dispatch_orchestrator",
        new=AsyncMock(),
    ):
        resp = await auth_client.post(
            f"/api/v1/workflows/{wf.id}/run-with-context",
            json={"context": "extra"},
        )
    assert resp.status_code != 409
    assert resp.status_code < 500


@pytest.mark.asyncio
async def test_run_with_context_workflow_inexistente_404(
    auth_client: AsyncClient,
):
    """Sanity: workflow inexistente sigue dando 404 (mapeo intacto)."""
    resp = await auth_client.post(
        f"/api/v1/workflows/{uuid4()}/run-with-context",
        json={"context": "x"},
    )
    assert resp.status_code == 404
