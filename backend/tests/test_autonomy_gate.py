"""Tests del autonomy_gate (AI.AGT wiring)."""
from uuid import uuid4

import pytest
from app.db.models.tasks import PendingApproval, Task
from app.services.autonomy import set_policy
from app.services.autonomy_gate import (
    AutonomyDecision,
    evaluate_autonomy,
    serialize_action_payload,
)
from sqlalchemy import select


@pytest.mark.asyncio
class TestEvaluate:
    async def test_default_banking_write_es_manual(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user

        decision = await evaluate_autonomy(
            db,
            tenant_id=tenant.id,
            domain="banking_write",
            action_summary="Transferir 100€",
            user_id=user.id,
        )

        assert decision.mode == "MANUAL"
        assert decision.manual_only is True
        assert decision.can_execute is False

    async def test_default_accounting_es_confirm(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        decision = await evaluate_autonomy(
            db,
            tenant_id=tenant.id,
            domain="accounting",
            action_summary="Crear asiento contable",
        )

        assert decision.mode == "CONFIRM"
        assert decision.needs_approval is True

    async def test_default_crm_es_auto(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        decision = await evaluate_autonomy(
            db,
            tenant_id=tenant.id,
            domain="crm",
            action_summary="Crear oportunidad",
        )

        assert decision.mode == "AUTO"
        assert decision.can_execute is True

    async def test_override_policy_se_respeta(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user

        await set_policy(db, tenant_id=tenant.id, domain="crm", mode="MANUAL")
        await db.commit()

        decision = await evaluate_autonomy(
            db, tenant_id=tenant.id, domain="crm",
            action_summary="Crear oportunidad",
        )
        assert decision.mode == "MANUAL"


@pytest.mark.asyncio
class TestPersistPendingApproval:
    async def _task(self, db, tenant_id, user_id):
        t = Task(
            tenant_id=tenant_id,
            created_by=user_id,
            domain="accounting",
            user_intent="Test gate",
            status="executing",
        )
        db.add(t)
        await db.flush()
        return t

    async def test_persiste_approval_en_modo_confirm(
        self, db, seed_tenant_and_user
    ):
        tenant, user, _t = seed_tenant_and_user
        task = await self._task(db, tenant.id, user.id)

        decision = await evaluate_autonomy(
            db, tenant_id=tenant.id, domain="accounting",
            action_summary="Crear asiento de gasto 121€",
            action_payload={"amount": 121.0, "account": "629"},
            user_id=user.id, task_id=task.id,
        )

        approval = await decision.persist_pending_approval(db)
        await db.commit()

        assert approval.id is not None
        assert approval.status == "pending"
        assert approval.action_description.startswith("Crear asiento")
        assert approval.action_payload["amount"] == 121.0

        # Persistido y consultable
        result = await db.execute(
            select(PendingApproval).where(PendingApproval.id == approval.id)
        )
        assert result.scalar_one_or_none() is not None

    async def test_rechaza_persistir_si_mode_no_confirm(
        self, db, seed_tenant_and_user
    ):
        tenant, user, _t = seed_tenant_and_user
        task = await self._task(db, tenant.id, user.id)

        decision = await evaluate_autonomy(
            db, tenant_id=tenant.id, domain="crm",
            action_summary="X",
            task_id=task.id, user_id=user.id,
        )
        assert decision.mode == "AUTO"

        with pytest.raises(ValueError, match="solo aplica en modo CONFIRM"):
            await decision.persist_pending_approval(db)

    async def test_requiere_task_id(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user

        decision = await evaluate_autonomy(
            db, tenant_id=tenant.id, domain="accounting",
            action_summary="X", user_id=user.id,
            # task_id omitido a propósito
        )

        with pytest.raises(ValueError, match="task_id es obligatorio"):
            await decision.persist_pending_approval(db)


class TestResponses:
    def test_suggestion_response_manual(self):
        decision = AutonomyDecision(
            mode="MANUAL",
            domain="banking_write",
            tenant_id=uuid4(),
            action_summary="Transferir",
            action_payload={"amount": 100},
        )
        resp = decision.to_suggestion_response()
        assert resp["executed"] is False
        assert resp["mode"] == "MANUAL"
        assert "MANUAL" in resp["reason"]

    def test_pending_response_confirm(self):
        decision = AutonomyDecision(
            mode="CONFIRM",
            domain="accounting",
            tenant_id=uuid4(),
            action_summary="Asiento",
        )
        approval_id = uuid4()
        resp = decision.to_pending_response(approval_id=approval_id)
        assert resp["executed"] is False
        assert resp["mode"] == "CONFIRM"
        assert resp["approval_id"] == str(approval_id)


class TestSerialize:
    def test_serialize_payload_acepta_uuid(self):
        out = serialize_action_payload({"id": uuid4(), "amount": 100})
        assert "id" in out
        assert "amount" in out
