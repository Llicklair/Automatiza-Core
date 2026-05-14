"""Tests para SEC.APR — MANDATORY_HUMAN_FISCAL + FiscalApprovalLog."""
from uuid import uuid4

import pytest

from app.db.models.tasks import (
    FiscalApprovalLog,
    PendingApproval,
    RISK_LEVEL_MANDATORY_HUMAN_FISCAL,
    Task,
)
from app.services.workflow.fiscal_approval import (
    approve_fiscal,
    build_expected_approval_text,
    compute_payload_hash,
    has_valid_fiscal_approval,
    reject_fiscal,
    request_fiscal_approval,
)


async def _seed_task(db, tenant_id):
    task = Task(
        tenant_id=tenant_id,
        domain="billing",
        user_intent="Presentar modelo 303 1T 2026",
        status="pending",
    )
    db.add(task)
    await db.flush()
    return task


@pytest.mark.asyncio
class TestComputePayloadHash:
    async def test_hash_determinista(self):
        a = compute_payload_hash({"a": 1, "b": 2})
        b = compute_payload_hash({"b": 2, "a": 1})  # orden distinto
        assert a == b
        assert len(a) == 64

    async def test_cambio_payload_cambia_hash(self):
        a = compute_payload_hash({"importe": 100})
        b = compute_payload_hash({"importe": 101})
        assert a != b


@pytest.mark.asyncio
class TestRequestFiscalApproval:
    async def test_crea_pending_approval_con_risk_level(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        task = await _seed_task(db, tenant.id)

        approval = await request_fiscal_approval(
            db,
            tenant_id=tenant.id,
            task_id=task.id,
            model_aeat="303",
            period_year=2026,
            period_quarter=1,
            payload={"total_devengado": 1000, "total_deducible": 200},
        )
        await db.commit()

        assert approval.risk_level == RISK_LEVEL_MANDATORY_HUMAN_FISCAL
        assert approval.status == "pending"
        assert "modelo 303" in approval.action_description
        assert "1T-2026" in approval.action_description


@pytest.mark.asyncio
class TestApproveFiscal:
    async def test_aprobacion_correcta_crea_log(self, db, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        task = await _seed_task(db, tenant.id)
        payload = {"total_devengado": 1000}

        approval = await request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="303", period_year=2026, period_quarter=1, payload=payload,
        )
        await db.flush()

        expected_text = build_expected_approval_text("303", "1T-2026")
        log = await approve_fiscal(
            db,
            pending_approval_id=approval.id,
            user_id=user.id,
            approval_text=expected_text,
            model_aeat="303",
            period_year=2026,
            period_quarter=1,
            payload=payload,
            ip_address="192.168.1.10",
            user_agent="Mozilla/5.0",
        )
        await db.commit()

        assert log.decision == "approved"
        assert log.model_aeat == "303"
        assert log.user_id == user.id
        assert log.ip_address == "192.168.1.10"
        assert log.payload_hash == compute_payload_hash(payload)
        # El PendingApproval debe quedar marcado como approved
        await db.refresh(approval)
        assert approval.status == "approved"
        assert approval.approved_by == user.id

    async def test_texto_incorrecto_lanza_value_error(self, db, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        task = await _seed_task(db, tenant.id)
        payload = {"x": 1}
        approval = await request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="111", period_year=2026, period_quarter=1, payload=payload,
        )
        await db.flush()

        with pytest.raises(ValueError, match="Texto de aprobación"):
            await approve_fiscal(
                db,
                pending_approval_id=approval.id,
                user_id=user.id,
                approval_text="ok",  # texto demasiado corto
                model_aeat="111",
                period_year=2026,
                period_quarter=1,
                payload=payload,
            )

    async def test_texto_sin_acentos_es_aceptado(self, db, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        task = await _seed_task(db, tenant.id)
        payload = {"x": 1}
        approval = await request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="303", period_year=2026, period_quarter=2, payload=payload,
        )
        await db.flush()

        # Mismo texto pero sin acentos (típico teclado físico simplificado)
        text_no_accents = (
            "Confirmo que he revisado los datos y asumo la responsabilidad "
            "de la presentacion ante AEAT del modelo 303 para el periodo 2T-2026"
        )
        log = await approve_fiscal(
            db,
            pending_approval_id=approval.id,
            user_id=user.id,
            approval_text=text_no_accents,
            model_aeat="303",
            period_year=2026,
            period_quarter=2,
            payload=payload,
        )
        assert log.decision == "approved"

    async def test_aprobacion_doble_falla(self, db, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        task = await _seed_task(db, tenant.id)
        payload = {"x": 1}
        approval = await request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="303", period_year=2026, period_quarter=1, payload=payload,
        )
        await db.flush()
        expected = build_expected_approval_text("303", "1T-2026")
        await approve_fiscal(
            db, pending_approval_id=approval.id, user_id=user.id,
            approval_text=expected, model_aeat="303",
            period_year=2026, period_quarter=1, payload=payload,
        )
        with pytest.raises(ValueError, match="ya cerrada"):
            await approve_fiscal(
                db, pending_approval_id=approval.id, user_id=user.id,
                approval_text=expected, model_aeat="303",
                period_year=2026, period_quarter=1, payload=payload,
            )


@pytest.mark.asyncio
class TestRejectFiscal:
    async def test_rechazo_crea_log_y_marca_pending(self, db, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        task = await _seed_task(db, tenant.id)
        payload = {"x": 1}
        approval = await request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="347", period_year=2026, period_quarter=None, payload=payload,
        )
        await db.flush()

        log = await reject_fiscal(
            db, pending_approval_id=approval.id, user_id=user.id,
            rejection_reason="Datos incompletos en proveedor X",
            model_aeat="347", period_year=2026, period_quarter=None, payload=payload,
        )
        await db.commit()

        assert log.decision == "rejected"
        assert "Datos incompletos" in log.rejection_reason
        await db.refresh(approval)
        assert approval.status == "rejected"


@pytest.mark.asyncio
class TestHasValidFiscalApproval:
    async def test_aprobacion_misma_payload_es_valida(self, db, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        task = await _seed_task(db, tenant.id)
        payload = {"total": 1000}
        approval = await request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="303", period_year=2026, period_quarter=1, payload=payload,
        )
        await db.flush()
        expected = build_expected_approval_text("303", "1T-2026")
        await approve_fiscal(
            db, pending_approval_id=approval.id, user_id=user.id,
            approval_text=expected, model_aeat="303",
            period_year=2026, period_quarter=1, payload=payload,
        )
        await db.commit()

        is_valid = await has_valid_fiscal_approval(
            db, tenant_id=tenant.id, model_aeat="303",
            period_year=2026, period_quarter=1,
            payload_hash=compute_payload_hash(payload),
        )
        assert is_valid is True

    async def test_aprobacion_payload_distinto_no_es_valida(self, db, seed_tenant_and_user):
        # Si el borrador cambia tras la aprobación, se requiere re-aprobar.
        tenant, user, _ = seed_tenant_and_user
        task = await _seed_task(db, tenant.id)
        payload_original = {"total": 1000}
        approval = await request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="303", period_year=2026, period_quarter=1, payload=payload_original,
        )
        await db.flush()
        expected = build_expected_approval_text("303", "1T-2026")
        await approve_fiscal(
            db, pending_approval_id=approval.id, user_id=user.id,
            approval_text=expected, model_aeat="303",
            period_year=2026, period_quarter=1, payload=payload_original,
        )
        await db.commit()

        # Verificar con un payload distinto al aprobado
        payload_modificado = {"total": 1500}
        is_valid = await has_valid_fiscal_approval(
            db, tenant_id=tenant.id, model_aeat="303",
            period_year=2026, period_quarter=1,
            payload_hash=compute_payload_hash(payload_modificado),
        )
        assert is_valid is False

    async def test_rechazo_no_cuenta_como_aprobacion(self, db, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        task = await _seed_task(db, tenant.id)
        payload = {"x": 1}
        approval = await request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="111", period_year=2026, period_quarter=1, payload=payload,
        )
        await db.flush()
        await reject_fiscal(
            db, pending_approval_id=approval.id, user_id=user.id,
            rejection_reason="No",
            model_aeat="111", period_year=2026, period_quarter=1, payload=payload,
        )
        await db.commit()

        is_valid = await has_valid_fiscal_approval(
            db, tenant_id=tenant.id, model_aeat="111",
            period_year=2026, period_quarter=1,
            payload_hash=compute_payload_hash(payload),
        )
        assert is_valid is False
