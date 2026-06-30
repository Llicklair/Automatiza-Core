"""update_candidate_status pasa por el gate de autonomía (recruitment=CONFIRM).

Antes el agente podía pasar un candidato a 'hired'/'rejected' sin aprobación
humana, incluso en un workflow desatendido. Ahora bajo CONFIRM queda pendiente
y NO se aplica; solo en AUTO se aplica directo.
"""

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.agents.recruitment.tools import update_candidate_status
from app.db.models.hr import Candidate
from app.services.autonomy import set_policy

pytestmark = pytest.mark.asyncio


def _patched_sessions(db):
    @asynccontextmanager
    async def ctx():
        yield db

    return (
        patch("app.db.base.AsyncSessionLocal", side_effect=ctx),
        patch("app.agents.recruitment.tools.AsyncSessionLocal", side_effect=ctx),
    )


async def _candidate(db, tenant_id) -> Candidate:
    c = Candidate(tenant_id=tenant_id, name="Juan Pérez", status="shortlisted")
    db.add(c)
    await db.flush()
    return c


async def test_confirm_no_aplica_el_estado(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    c = await _candidate(db, tenant.id)
    await db.commit()

    p1, p2 = _patched_sessions(db)
    with p1, p2:
        res = await update_candidate_status.coroutine(
            tenant_id=str(tenant.id), candidate_id=str(c.id), new_status="hired"
        )

    assert "pendiente" in res.lower() or "aprob" in res.lower(), res
    refreshed = (await db.execute(select(Candidate).where(Candidate.id == c.id))).scalar_one()
    assert refreshed.status == "shortlisted", "no debe aplicarse bajo CONFIRM"


async def test_auto_aplica_el_estado(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    await set_policy(db, tenant_id=tenant.id, domain="recruitment", mode="AUTO")
    c = await _candidate(db, tenant.id)
    await db.commit()

    p1, p2 = _patched_sessions(db)
    with p1, p2:
        res = await update_candidate_status.coroutine(
            tenant_id=str(tenant.id), candidate_id=str(c.id), new_status="hired"
        )

    assert "hired" in res
    refreshed = (await db.execute(select(Candidate).where(Candidate.id == c.id))).scalar_one()
    assert refreshed.status == "hired"
