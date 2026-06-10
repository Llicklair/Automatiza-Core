"""Blindaje fiscal: Verifactu/AEAT nunca se auto-presenta.

Garantías que verifica este módulo:
  1. El dominio `fiscal` está forzado a MANUAL y no es configurable
     (ni por servicio ni aunque exista una fila persistida en DB).
  2. `submit_signed_xml` con dry_run=False sin `confirmed=True` lanza SedeError.
  3. `submit_presentation` con dry_run=False sin `confirmed_by_user_id` lanza
     PresentationError.
"""

import uuid

import pytest

from app.services.autonomy import FORCED_MODES, check_autonomy, default_mode, set_policy

pytestmark = pytest.mark.asyncio


async def test_fiscal_forced_manual_default():
    assert FORCED_MODES["fiscal"] == "MANUAL"
    assert default_mode("fiscal") == "MANUAL"


async def test_set_policy_fiscal_auto_rejected(db, seed_tenant_and_user):
    tenant, _user, _token = seed_tenant_and_user
    with pytest.raises(ValueError, match="forzado"):
        await set_policy(db, tenant_id=tenant.id, domain="fiscal", mode="AUTO")
    with pytest.raises(ValueError, match="forzado"):
        await set_policy(db, tenant_id=tenant.id, domain="fiscal", mode="CONFIRM")


async def test_fiscal_manual_even_with_persisted_row(db, seed_tenant_and_user):
    """Aunque alguien escriba AUTO a mano en la tabla, el gate devuelve MANUAL."""
    from app.db.models.tenant import AutonomyPolicy

    tenant, _user, _token = seed_tenant_and_user
    db.add(AutonomyPolicy(tenant_id=tenant.id, domain="fiscal", mode="AUTO"))
    await db.flush()

    mode = await check_autonomy(db, tenant_id=tenant.id, domain="fiscal")
    assert mode == "MANUAL"


async def test_put_policy_fiscal_auto_rejected_via_api(auth_client):
    resp = await auth_client.put("/api/v1/autonomy/fiscal", json={"mode": "AUTO"})
    assert resp.status_code == 400
    assert "forzado" in resp.json()["detail"]


async def test_sede_real_submission_requires_confirmation():
    from app.services.aeat.sede_client import SedeError, submit_signed_xml

    with pytest.raises(SedeError, match="confirmación humana"):
        await submit_signed_xml("303", "<xml/>", dry_run=False)


async def test_submit_presentation_requires_confirmed_user(db, seed_tenant_and_user):
    from app.services.aeat.presentation_service import PresentationError, submit_presentation

    tenant, _user, _token = seed_tenant_and_user
    with pytest.raises(PresentationError, match="confirmación humana"):
        await submit_presentation(
            db, tenant.id, uuid.uuid4(), dry_run=False, confirmed_by_user_id=None
        )
