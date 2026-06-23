"""Cobertura del path crítico de dispatch del scheduler (cada minuto).

`tasks_scheduler._check_scheduled_workflows` es el loop cross-tenant que
APScheduler dispara con `CronTrigger(minute='*')`. Hasta ahora SOLO estaban
testeados sus helpers DB sueltos (`test_service_workflow_scheduler.py`) y el
puro `_next_due_run` (`test_scheduler_next_due_run.py`); el loop end-to-end
—routing de dominio, gates de idempotencia/condiciones/ejecución-activa, rama
determinista vs reasoning y AISLAMIENTO de fallos— no tenía ninguna prueba.

Patrón (igual que `test_workflow_failure_alerts.py`): el worker abre su PROPIA
sesión vía `AsyncSessionLocal`, así que sembramos y verificamos con bloques
`async with AsyncSessionLocal()` propios (no la fixture `db`). `dispatch_orchestrator`
/ `execute_deterministic_steps` se mockean con `AsyncMock`, y `IdempotencyGuard`
se sustituye por un fake en memoria (sin Redis/DB, determinista).
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

import app.workers.tasks_scheduler as ts
from app.db.base import AsyncSessionLocal
from app.db.models.models import Task, Tenant, Workflow, WorkflowExecution

# Cron que vence cada minuto → `_next_due_run` siempre devuelve un instante
# vencido dentro de la ventana de gracia (workflow "due" de forma determinista).
DUE_CRON = "* * * * *"


# ---------------------------------------------------------------------------
# Helpers de sembrado / consulta (sesión propia, como el worker)
# ---------------------------------------------------------------------------


async def _seed_workflow(**overrides) -> tuple:
    """Crea un tenant + un Workflow schedule_based; devuelve (tenant_id, wf_id)."""
    async with AsyncSessionLocal() as db:
        tenant = Tenant(id=uuid4(), name="Sched Disp", nif=f"D{uuid4().int % 10**8:08d}")
        db.add(tenant)
        await db.flush()
        defaults = dict(
            id=uuid4(),
            tenant_id=tenant.id,
            name="WF",
            trigger_type="schedule_based",
            action_type="prompt",
            is_active=True,
            trigger_config={"cron": DUE_CRON},
        )
        defaults.update(overrides)
        wf = Workflow(**defaults)
        db.add(wf)
        await db.commit()
        return tenant.id, wf.id


async def _add_execution(wf_id, tenant_id, status="running") -> None:
    async with AsyncSessionLocal() as db:
        db.add(WorkflowExecution(id=uuid4(), workflow_id=wf_id, tenant_id=tenant_id, status=status))
        await db.commit()


async def _executions(wf_id) -> list:
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(WorkflowExecution).where(WorkflowExecution.workflow_id == wf_id))
        return list(res.scalars().all())


async def _tasks(tenant_id) -> list:
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Task).where(Task.tenant_id == tenant_id))
        return list(res.scalars().all())


def _install_fake_guard(monkeypatch, already=False) -> tuple[list, list]:
    """Sustituye IdempotencyGuard por un fake; devuelve (marked, released)."""
    marked: list = []
    released: list = []

    class _FakeGuard:
        def __init__(self, ttl: int = 0):
            pass

        async def already_executed(self, op, key):
            return already

        async def mark_executed(self, op, key, summary=None):
            marked.append((op, key))

        async def release(self, op, key):
            released.append((op, key))

    monkeypatch.setattr(ts, "IdempotencyGuard", _FakeGuard)
    return marked, released


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_due_workflow_dispatches_reasoning(monkeypatch):
    """Un workflow vencido crea Execution + Task e invoca dispatch_orchestrator
    una vez con el tenant correcto; la clave de idempotencia se marca."""
    tid, wf_id = await _seed_workflow(action_config={"instruction": "factura vencida"})
    dispatch = AsyncMock()
    monkeypatch.setattr(ts, "dispatch_orchestrator", dispatch)
    marked, released = _install_fake_guard(monkeypatch)

    await ts._check_scheduled_workflows()

    dispatch.assert_awaited_once()
    assert dispatch.await_args.kwargs["tenant_id"] == str(tid)

    execs = await _executions(wf_id)
    assert len(execs) == 1
    assert execs[0].status == "running"  # el orchestrator (mockeado) la cerraría luego
    tasks = await _tasks(tid)
    assert len(tasks) == 1
    assert tasks[0].domain == "billing"
    assert tasks[0].status == "pending"
    assert execs[0].task_id == tasks[0].id
    # Idempotencia: clave "<wf_id>:<YYYYMMDDHHMM>" (instante programado, no el tick).
    assert len(marked) == 1
    assert marked[0][1].startswith(f"{wf_id}:")
    assert released == []


@pytest.mark.parametrize(
    "instruction,expected",
    [
        ("factura vencida sin cobrar", "billing"),
        ("genera la nomina de los empleados", "hr"),
        ("revisa el iva del trimestre", "advisory"),
        ("prepara el resumen de la semana", "chat"),  # sin keyword → coordinador LLM
    ],
)
async def test_domain_routing_from_keywords(monkeypatch, instruction, expected):
    """El routing por keywords coloca la Task en el dominio correcto; sin match → 'chat'."""
    tid, _wf_id = await _seed_workflow(action_config={"instruction": instruction})
    monkeypatch.setattr(ts, "dispatch_orchestrator", AsyncMock())
    _install_fake_guard(monkeypatch)

    await ts._check_scheduled_workflows()

    tasks = await _tasks(tid)
    assert len(tasks) == 1
    assert tasks[0].domain == expected


async def test_explicit_domain_overrides_inference(monkeypatch):
    """action_config['domain'] explícito gana sobre la inferencia por keywords."""
    tid, _wf_id = await _seed_workflow(action_config={"domain": "banking", "instruction": "factura vencida"})
    monkeypatch.setattr(ts, "dispatch_orchestrator", AsyncMock())
    _install_fake_guard(monkeypatch)

    await ts._check_scheduled_workflows()

    tasks = await _tasks(tid)
    assert tasks[0].domain == "banking"  # NO "billing" pese a "factura"


async def test_deterministic_workflow_runs_steps_not_orchestrator(monkeypatch):
    """execution_mode='deterministic' con compiled_steps corre execute_deterministic_steps
    y NUNCA llama a dispatch_orchestrator; la execution queda 'success'."""
    tid, wf_id = await _seed_workflow(
        execution_mode="deterministic",
        compiled_steps=[{"agent": "billing", "action": "noop"}],
    )
    steps = AsyncMock(return_value=[{"agent": "billing", "success": True}])
    dispatch = AsyncMock()
    monkeypatch.setattr(ts, "execute_deterministic_steps", steps)
    monkeypatch.setattr(ts, "dispatch_orchestrator", dispatch)
    marked, _ = _install_fake_guard(monkeypatch)

    await ts._check_scheduled_workflows()

    steps.assert_awaited_once()
    dispatch.assert_not_awaited()
    execs = await _executions(wf_id)
    assert execs[0].status == "success"
    assert "OK" in (execs[0].result_log or "")
    tasks = await _tasks(tid)
    assert tasks[0].domain == "deterministic"
    assert tasks[0].status == "done"
    assert len(marked) == 1


async def test_failing_execution_is_isolated(monkeypatch):
    """Una excepción al despachar un workflow NO aborta el loop: el segundo
    workflow vencido se despacha igual, y el que falla queda 'failed'."""
    tid_a, wf_a = await _seed_workflow(action_config={"instruction": "factura A"})
    tid_b, wf_b = await _seed_workflow(action_config={"instruction": "factura B"})

    def _side(task_id, tenant_id=None):
        if tenant_id == str(tid_a):
            raise RuntimeError("boom")

    dispatch = AsyncMock(side_effect=_side)
    monkeypatch.setattr(ts, "dispatch_orchestrator", dispatch)
    marked, released = _install_fake_guard(monkeypatch)

    await ts._check_scheduled_workflows()  # no debe propagar la excepción

    assert dispatch.await_count == 2  # ambos intentados → el fallo de A no cortó el loop
    seen = {c.kwargs["tenant_id"] for c in dispatch.await_args_list}
    assert seen == {str(tid_a), str(tid_b)}

    ex_a = (await _executions(wf_a))[0]
    ex_b = (await _executions(wf_b))[0]
    assert ex_a.status == "failed"
    assert "Error lanzando orchestrator" in (ex_a.result_log or "")
    assert ex_b.status == "running"  # B intacto

    assert any(k.startswith(f"{wf_a}:") for _, k in released)  # A liberó su clave
    assert any(k.startswith(f"{wf_b}:") for _, k in marked)  # B marcó la suya


async def test_no_due_workflows_is_noop(monkeypatch):
    """Sin workflows vencidos (sin cron / inactivo / no schedule_based) no hay
    dispatch ni ejecuciones creadas."""
    await _seed_workflow(trigger_config={})  # schedule_based activo SIN cron → due_run None
    await _seed_workflow(is_active=False)  # inactivo → fuera de la query
    await _seed_workflow(trigger_type="event_based")  # no schedule_based → fuera de la query
    dispatch = AsyncMock()
    monkeypatch.setattr(ts, "dispatch_orchestrator", dispatch)
    _install_fake_guard(monkeypatch)

    await ts._check_scheduled_workflows()

    dispatch.assert_not_awaited()
    async with AsyncSessionLocal() as db:
        total = (await db.execute(select(WorkflowExecution))).scalars().all()
    assert list(total) == []


async def test_active_execution_skips_dispatch(monkeypatch):
    """Un workflow vencido con una ejecución running/pending se salta (gate
    has_active_execution): ni dispatch ni nueva ejecución."""
    tid, wf_id = await _seed_workflow(action_config={"instruction": "factura vencida"})
    await _add_execution(wf_id, tid, status="running")
    dispatch = AsyncMock()
    monkeypatch.setattr(ts, "dispatch_orchestrator", dispatch)
    _install_fake_guard(monkeypatch)

    await ts._check_scheduled_workflows()

    dispatch.assert_not_awaited()
    execs = await _executions(wf_id)
    assert len(execs) == 1  # solo la preexistente; no se creó otra


async def test_idempotency_guard_prevents_double_fire(monkeypatch):
    """Si la clave (workflow, minuto-programado) ya consta ejecutada, el workflow
    se salta aunque su cron esté vencido — protege contra un tick retrasado/reintentado."""
    tid, wf_id = await _seed_workflow(action_config={"instruction": "factura vencida"})
    dispatch = AsyncMock()
    monkeypatch.setattr(ts, "dispatch_orchestrator", dispatch)
    _install_fake_guard(monkeypatch, already=True)  # ya ejecutada

    await ts._check_scheduled_workflows()

    dispatch.assert_not_awaited()
    assert await _executions(wf_id) == []  # ni siquiera se crea la ejecución
