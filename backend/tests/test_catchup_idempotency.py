"""Idempotencia del catchup de arranque: dos llamadas a _catchup_missed_workflows
para el mismo instante perdido deben crear exactamente UNA ejecucion.

El guard (IdempotencyGuard) corre contra la DB de test real (SQLite en memoria,
misma _TestSessionLocal que conftest.py ya inyecta en app.db.base). La funcion
_dispatch_workflow se parchea con un spy para no ejecutar pasos reales.

El test es EMPIRICO: no mockea el guard — deja que persista la clave de
idempotencia en la DB y comprueba que la segunda llamada la detecta y hace skip.

Control assertion: dos workflows DISTINTOS con el mismo cron perdido deben
dispararse ambos en la primera llamada (dispatch_count == 2), lo que demuestra
que el spy distingue un dispatch real de un skip.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select

import app.services.idempotency as idem
import app.workers.tasks_scheduler as ts
from app.db.base import AsyncSessionLocal
from app.db.models.models import Tenant, Workflow, WorkflowExecution

pytestmark = pytest.mark.asyncio

# Cron que vence cada minuto. Con created_at en el pasado el catchup
# siempre encuentra un next_run <= now.
DUE_CRON = "* * * * *"

# Cuanto tiempo atras sembramos el workflow: suficiente para que
# croniter("* * * * *", since_local).get_next() caiga en el pasado.
_PAST = timedelta(hours=2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_workflow(**overrides) -> tuple:
    """Crea un tenant + un Workflow schedule_based sin ejecuciones previas.

    created_at se fija 2 h en el pasado para que _catchup_missed_workflows
    calcule next_run <= now y entre en la rama de dispatch.
    """
    past = datetime.now(UTC) - _PAST
    async with AsyncSessionLocal() as db:
        tenant = Tenant(
            id=uuid4(),
            name="Catchup Test",
            nif=f"C{uuid4().int % 10**8:08d}",
        )
        db.add(tenant)
        await db.flush()
        defaults = dict(
            id=uuid4(),
            tenant_id=tenant.id,
            name="WF-catchup",
            trigger_type="schedule_based",
            action_type="prompt",
            is_active=True,
            trigger_config={"cron": DUE_CRON},
            created_at=past,
        )
        defaults.update(overrides)
        wf = Workflow(**defaults)
        db.add(wf)
        await db.commit()
        return tenant.id, wf.id


async def _executions(wf_id) -> list:
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.workflow_id == wf_id)
        )
        return list(res.scalars().all())


@pytest.fixture(autouse=True)
def _clean_idem_store():
    """Limpia el store en memoria antes/despues de cada test para no contaminar."""
    idem._store.clear()
    yield
    idem._store.clear()


def _make_dispatch_spy():
    """Devuelve un callable spy que registra llamadas y marca la clave de idempotencia.

    No ejecuta pasos reales. Llama a guard.mark_executed para que el guard
    persista la clave en DB, igual que lo haria el dispatch real en happy-path.
    """
    calls: list = []

    async def _spy(db, wf, execution, trigger_source, guard=None, idempotency_key=None):
        calls.append((str(wf.id), idempotency_key))
        if guard and idempotency_key:
            await guard.mark_executed("workflow_beat", idempotency_key)
        execution.status = "running"

    return _spy, calls


# ---------------------------------------------------------------------------
# Test principal: idempotencia del catchup
# ---------------------------------------------------------------------------


async def test_catchup_double_startup_dispatches_once():
    """Dos llamadas consecutivas a _catchup_missed_workflows para el mismo
    workflow con un instante perdido deben resultar en dispatch_count == 1.

    Primera llamada: guarda la clave en DB + crea execution.
    Segunda llamada: guard.already_executed detecta la clave en DB -> skip.
    La memoria (_store) se borra entre llamadas para simular que son dos
    instancias/procesos distintos que no comparten estado en memoria.
    """
    _tid, wf_id = await _seed_workflow()
    spy, calls = _make_dispatch_spy()

    with patch.object(ts, "_dispatch_workflow", wraps=spy):
        # Primera "instancia" del app arrancando.
        await ts._catchup_missed_workflows()

        # Simular reinicio/segunda instancia concurrente:
        # la memoria se borra pero la DB persiste la clave.
        idem._store.clear()

        # Segunda "instancia" arrancando al mismo tiempo.
        await ts._catchup_missed_workflows()

    # ASSERTION PRINCIPAL: el guard debe haber impedido el segundo dispatch.
    assert len(calls) == 1, (
        f"Se esperaba 1 dispatch pero hubo {len(calls)}. "
        "El guard de idempotencia del catchup no funciono."
    )
    # La primera llamada si dispatcho (calls[0] contiene el wf_id correcto).
    assert calls[0][0] == str(wf_id)

    # Solo debe existir la ejecucion creada en la primera llamada.
    execs = await _executions(wf_id)
    assert len(execs) == 1


# ---------------------------------------------------------------------------
# Control assertion: dos workflows DISTINTOS -> dos dispatches en primera llamada
# ---------------------------------------------------------------------------


async def test_catchup_two_distinct_workflows_dispatch_twice():
    """Control: con dos workflows distintos ambos se despachan en la primera llamada.

    Demuestra que el spy detecta dispatches reales y que el test principal
    no es tautologico: si el guard no existiera, la segunda llamada sobre el
    MISMO workflow tambien dispararia (como aqui lo hacen dos workflows distintos).
    """
    _tid_a, wf_id_a = await _seed_workflow()
    _tid_b, wf_id_b = await _seed_workflow()
    spy, calls = _make_dispatch_spy()

    with patch.object(ts, "_dispatch_workflow", wraps=spy):
        await ts._catchup_missed_workflows()

    # Ambos workflows deben haberse despachado exactamente una vez.
    assert len(calls) == 2
    dispatched_ids = {c[0] for c in calls}
    assert str(wf_id_a) in dispatched_ids
    assert str(wf_id_b) in dispatched_ids
