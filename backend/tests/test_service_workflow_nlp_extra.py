"""Tests adicionales para app.services.workflow._nlp.

Cubre los gaps de test_service_workflow_parse_nl.py:
  - _load_tenant_employees (filtros y manejo de errores)
  - fire_event (matching de eventos, conditions, dispatch deterministic vs reasoning)
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.db.models.ai_employees import AIEmployee
from app.db.models.models import Tenant, Workflow
from app.services.workflow._nlp import _load_tenant_employees, fire_event


@pytest.fixture
async def _tenant(db):
    t = Tenant(id=uuid4(), name="Test NLP", nif=f"N{uuid4().int % 10**8:08d}")
    db.add(t)
    await db.commit()
    return t


async def _make_employee(db, tenant_id, status="idle", is_builtin=True):
    e = AIEmployee(
        tenant_id=tenant_id,
        name=f"Emp-{uuid4().hex[:6]}",
        role="dev",
        domain="billing",
        is_builtin=is_builtin,
        status=status,
        system_prompt="x",
        icon="x",
        avatar_color="#fff",
    )
    db.add(e)
    await db.commit()
    return e


async def _make_workflow(db, tenant_id, **overrides):
    defaults = dict(
        tenant_id=tenant_id,
        name="WF",
        trigger_type="event_based",
        trigger_config={"events": ["new_invoice"]},
        action_type="prompt",
        action_config={"instruction": "fact"},
        is_active=True,
        execution_mode="reasoning",
    )
    defaults.update(overrides)
    wf = Workflow(**defaults)
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return wf


# ── _load_tenant_employees ───────────────────────────────────────────────────


@pytest.mark.asyncio
class TestLoadTenantEmployees:
    async def test_tenant_id_None_devuelve_vacio(self):
        assert await _load_tenant_employees(None) == []

    async def test_tenant_id_vacio_devuelve_vacio(self):
        assert await _load_tenant_employees("") == []

    async def test_filtra_por_status_activo(self, db, _tenant):
        idle = await _make_employee(db, _tenant.id, status="idle")
        working = await _make_employee(db, _tenant.id, status="working")
        pending = await _make_employee(db, _tenant.id, status="pending_setup")
        blocked = await _make_employee(db, _tenant.id, status="blocked")
        # blocked debe quedar fuera (status NO en idle/working/pending_setup)

        result = await _load_tenant_employees(_tenant.id)
        ids = {e.id for e in result}
        assert idle.id in ids
        assert working.id in ids
        assert pending.id in ids
        assert blocked.id not in ids

    async def test_aislamiento_por_tenant(self, db, _tenant):
        other = Tenant(id=uuid4(), name="Other", nif=f"O{uuid4().int % 10**8:08d}")
        db.add(other)
        await db.commit()
        mine = await _make_employee(db, _tenant.id, status="idle")
        theirs = await _make_employee(db, other.id, status="idle")

        result = await _load_tenant_employees(_tenant.id)
        ids = {e.id for e in result}
        assert mine.id in ids
        assert theirs.id not in ids

    async def test_db_error_devuelve_vacio_sin_crashear(self):
        """Errores de DB se loguean a debug y devuelven [] (best-effort)."""
        with patch(
            "app.services.workflow._nlp.AsyncSessionLocal",
            side_effect=RuntimeError("no DB"),
        ):
            result = await _load_tenant_employees(uuid4())
        assert result == []


# ── fire_event ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestFireEvent:
    async def test_sin_workflows_devuelve_vacio(self, db, _tenant):
        result = await fire_event("any_event", {}, _tenant.id, uuid4(), db)
        assert result == []

    async def test_workflow_inactivo_no_dispara(self, db, _tenant):
        await _make_workflow(db, _tenant.id, is_active=False)
        result = await fire_event("new_invoice", {}, _tenant.id, uuid4(), db)
        assert result == []

    async def test_evento_no_coincide_skip(self, db, _tenant):
        await _make_workflow(db, _tenant.id, trigger_config={"events": ["new_invoice"]})
        result = await fire_event("payroll_due", {}, _tenant.id, uuid4(), db)
        assert result == []

    async def test_evento_any_coincide_con_cualquiera(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id, trigger_config={"events": ["any"]})
        with patch(
            "app.services.workflow._execution._dispatch_reasoning",
            new=AsyncMock(),
        ) as mock_disp:
            await fire_event("whatever_event", {"x": 1}, _tenant.id, uuid4(), db)
        mock_disp.assert_awaited()

    async def test_condition_falsa_bloquea_dispatch(self, db, _tenant):
        # Condition que NUNCA se cumple (campo X != esperado)
        await _make_workflow(
            db, _tenant.id,
            trigger_config={
                "events": ["new_invoice"],
                "conditions": {"field": "amount", "op": "gt", "value": 1000},
            },
        )
        with patch(
            "app.services.workflow._execution._dispatch_reasoning",
            new=AsyncMock(),
        ) as mock_disp:
            # amount=10 < 1000 → condition falsa → skip
            result = await fire_event("new_invoice", {"amount": 10}, _tenant.id, uuid4(), db)
        mock_disp.assert_not_awaited()
        assert result == []

    async def test_condition_verdadera_lanza(self, db, _tenant):
        await _make_workflow(
            db, _tenant.id,
            trigger_config={
                "events": ["new_invoice"],
                "conditions": {"field": "amount", "op": "gt", "value": 100},
            },
        )
        with patch(
            "app.services.workflow._execution._dispatch_reasoning",
            new=AsyncMock(),
        ) as mock_disp:
            # amount=500 > 100 → dispara
            await fire_event("new_invoice", {"amount": 500}, _tenant.id, uuid4(), db)
        mock_disp.assert_awaited()

    async def test_deterministic_path_se_invoca_si_modo_determinista_y_compiled_steps(
        self, db, _tenant
    ):
        wf = await _make_workflow(
            db, _tenant.id,
            execution_mode="deterministic",
            compiled_steps=[{"agent": "billing", "tool": "list_invoices", "params": {}}],
        )

        async def fake_det(db, wf, ex, *args, **kwargs):
            ex.status = "success"

        with patch(
            "app.services.workflow._execution._dispatch_deterministic",
            new=AsyncMock(side_effect=fake_det),
        ) as mock_det:
            result = await fire_event("new_invoice", {}, _tenant.id, uuid4(), db)
        mock_det.assert_awaited()
        assert str(wf.id) in result

    async def test_reasoning_path_si_no_es_determinista(self, db, _tenant):
        wf = await _make_workflow(db, _tenant.id, execution_mode="reasoning")
        with patch(
            "app.services.workflow._execution._dispatch_reasoning",
            new=AsyncMock(),
        ) as mock_reasoning:
            result = await fire_event("new_invoice", {"x": "y"}, _tenant.id, uuid4(), db)
        mock_reasoning.assert_awaited()
        # El intent enriquecido incluye el evento
        call_args = mock_reasoning.await_args
        intent = call_args.args[5] if len(call_args.args) > 5 else call_args.kwargs.get("intent", "")
        assert "new_invoice" in intent

    async def test_aislamiento_por_tenant(self, db, _tenant):
        """fire_event de un tenant NO dispara workflows de otros tenants."""
        other = Tenant(id=uuid4(), name="Other", nif=f"O{uuid4().int % 10**8:08d}")
        db.add(other)
        await db.commit()
        await _make_workflow(db, other.id, trigger_config={"events": ["new_invoice"]})

        with patch(
            "app.services.workflow._execution._dispatch_reasoning",
            new=AsyncMock(),
        ) as mock_disp:
            result = await fire_event("new_invoice", {}, _tenant.id, uuid4(), db)
        assert result == []
        mock_disp.assert_not_awaited()
