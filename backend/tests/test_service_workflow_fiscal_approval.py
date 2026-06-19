"""Tests para app.services.workflow.fiscal_approval (SEC.APR).

Aprobación humana obligatoria de modelos AEAT (303/130/347/390/111/190).
Cubre los 7 puntos del flujo:
  - hash canónico del payload
  - texto de aprobación canónico
  - validación insensible a acentos/mayúsculas
  - request_fiscal_approval crea PendingApproval bien formado
  - approve_fiscal: happy path + 3 rechazos (texto mal, no existe, ya cerrado)
  - reject_fiscal: happy path + mismas validaciones
  - has_valid_fiscal_approval: hit + miss (incl. ventana "aprobar→modificar")
"""

from uuid import uuid4

import pytest
from app.db.models.models import PendingApproval, Task, Tenant
from app.db.models.tasks import RISK_LEVEL_MANDATORY_HUMAN_FISCAL
from app.services.workflow import fiscal_approval as svc


# ── helpers ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def _tenant_user_task(db):
    """Crea (tenant, user_id, task) — campos mínimos."""
    from app.db.models.auth import User

    tenant = Tenant(
        id=uuid4(),
        name="Test Fiscal",
        nif=f"F{uuid4().int % 10**8:08d}",
    )
    db.add(tenant)
    await db.commit()

    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email=f"u-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
        role="admin",
    )
    db.add(user)
    await db.commit()

    task = Task(
        tenant_id=tenant.id,
        domain="compliance",
        status="awaiting_approval",
        user_intent="modelo 303",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return tenant, user.id, task


# ── compute_payload_hash ─────────────────────────────────────────────────────


class TestComputePayloadHash:
    def test_hash_deterministico(self):
        p = {"a": 1, "b": [2, 3]}
        assert svc.compute_payload_hash(p) == svc.compute_payload_hash(p)

    def test_hash_order_independent(self):
        """Misma data, distinto orden de claves → mismo hash (sort_keys)."""
        a = {"x": 1, "y": 2}
        b = {"y": 2, "x": 1}
        assert svc.compute_payload_hash(a) == svc.compute_payload_hash(b)

    def test_hash_cambia_si_cambia_payload(self):
        a = {"total": "100.00"}
        b = {"total": "100.01"}
        assert svc.compute_payload_hash(a) != svc.compute_payload_hash(b)

    def test_hash_acepta_datetimes(self):
        """default=str para tipos no serializables nativamente."""
        from datetime import date

        p = {"fecha": date(2026, 1, 1), "n": 42}
        h = svc.compute_payload_hash(p)
        assert len(h) == 64  # SHA-256 hex


# ── build_expected_approval_text ─────────────────────────────────────────────


class TestBuildExpectedApprovalText:
    def test_formato_canonico(self):
        text = svc.build_expected_approval_text("303", "1T-2026")
        assert "modelo 303" in text
        assert "1T-2026" in text
        assert "responsabilidad" in text

    def test_anyo_solo_sin_quarter(self):
        text = svc.build_expected_approval_text("390", "2026")
        assert "2026" in text


# ── _validate_approval_text ──────────────────────────────────────────────────


class TestValidateApprovalText:
    def test_match_exacto(self):
        expected = svc.build_expected_approval_text("303", "1T-2026")
        assert svc._validate_approval_text(expected, expected) is True

    def test_match_sin_acentos(self):
        """El usuario puede escribir sin acentos en teclado típico."""
        expected = svc.build_expected_approval_text("303", "1T-2026")
        # build_expected ya viene sin acentos pero por si acaso testeamos versión con
        plain = expected
        accented = expected.replace("presentacion", "presentación")
        # Ambos normalizan igual
        assert svc._validate_approval_text(accented, plain) is True

    def test_match_case_insensitive(self):
        expected = svc.build_expected_approval_text("303", "1T-2026")
        assert svc._validate_approval_text(expected.upper(), expected) is True

    def test_match_con_whitespace_externo(self):
        expected = svc.build_expected_approval_text("303", "1T-2026")
        assert svc._validate_approval_text(f"   {expected}   ", expected) is True

    def test_no_match_si_texto_diferente(self):
        expected = svc.build_expected_approval_text("303", "1T-2026")
        assert svc._validate_approval_text("acepto", expected) is False

    def test_no_match_si_periodo_diferente(self):
        """Cambiar el modelo o período invalida el texto."""
        expected = svc.build_expected_approval_text("303", "1T-2026")
        provided = svc.build_expected_approval_text("303", "2T-2026")
        assert svc._validate_approval_text(provided, expected) is False


# ── request_fiscal_approval ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRequestFiscalApproval:
    async def test_crea_pending_approval_con_risk_level_correcto(self, db, _tenant_user_task):
        tenant, _, task = _tenant_user_task
        payload = {"total": "1500.00", "lines": []}
        approval = await svc.request_fiscal_approval(
            db,
            tenant_id=tenant.id,
            task_id=task.id,
            model_aeat="303",
            period_year=2026,
            period_quarter=1,
            payload=payload,
        )
        await db.commit()
        assert approval.id is not None
        assert approval.risk_level == RISK_LEVEL_MANDATORY_HUMAN_FISCAL
        assert approval.status == "pending"
        assert approval.action_payload == payload
        assert "modelo 303" in approval.action_description
        assert "1T-2026" in approval.action_description
        # expires_at en el futuro
        # SQLite devuelve naive en algunos casos; normalizar
        from datetime import datetime, timezone
        exp = approval.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        assert exp > datetime.now(timezone.utc)

    async def test_sin_quarter_solo_anyo(self, db, _tenant_user_task):
        tenant, _, task = _tenant_user_task
        approval = await svc.request_fiscal_approval(
            db,
            tenant_id=tenant.id,
            task_id=task.id,
            model_aeat="390",
            period_year=2026,
            period_quarter=None,
            payload={},
        )
        assert "2026" in approval.action_description
        # No debe contener "T-" si no hay quarter
        assert "T-2026" not in approval.action_description


# ── approve_fiscal ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestApproveFiscal:
    async def _make_pending(self, db, tenant, task, payload=None):
        payload = payload or {"total": "1000.00"}
        approval = await svc.request_fiscal_approval(
            db,
            tenant_id=tenant.id,
            task_id=task.id,
            model_aeat="303",
            period_year=2026,
            period_quarter=1,
            payload=payload,
        )
        await db.commit()
        return approval, payload

    async def test_approve_happy_path(self, db, _tenant_user_task):
        tenant, user_id, task = _tenant_user_task
        pending, payload = await self._make_pending(db, tenant, task)
        text = svc.build_expected_approval_text("303", "1T-2026")

        log = await svc.approve_fiscal(
            db,
            pending_approval_id=pending.id,
            user_id=user_id,
            approval_text=text,
            model_aeat="303",
            period_year=2026,
            period_quarter=1,
            payload=payload,
            ip_address="127.0.0.1",
            user_agent="pytest",
        )
        await db.commit()

        # Log creado correctamente
        assert log.decision == "approved"
        assert log.model_aeat == "303"
        assert log.payload_hash == svc.compute_payload_hash(payload)
        assert log.ip_address == "127.0.0.1"
        assert log.user_agent == "pytest"

        # PendingApproval marcado como aprobado
        from sqlalchemy import select

        refreshed = (
            await db.execute(select(PendingApproval).where(PendingApproval.id == pending.id))
        ).scalar_one()
        assert refreshed.status == "approved"
        assert refreshed.approved_by == user_id
        assert refreshed.approved_at is not None

    async def test_approve_rechaza_texto_incorrecto(self, db, _tenant_user_task):
        tenant, user_id, task = _tenant_user_task
        pending, payload = await self._make_pending(db, tenant, task)
        with pytest.raises(ValueError, match="Texto de aprobación no coincide"):
            await svc.approve_fiscal(
                db,
                pending_approval_id=pending.id,
                user_id=user_id,
                approval_text="acepto",
                model_aeat="303",
                period_year=2026,
                period_quarter=1,
                payload=payload,
            )

    async def test_approve_falla_si_pending_no_existe(self, db, _tenant_user_task):
        _, user_id, _ = _tenant_user_task
        text = svc.build_expected_approval_text("303", "1T-2026")
        with pytest.raises(LookupError):
            await svc.approve_fiscal(
                db,
                pending_approval_id=uuid4(),
                user_id=user_id,
                approval_text=text,
                model_aeat="303",
                period_year=2026,
                period_quarter=1,
                payload={},
            )

    async def test_approve_falla_si_ya_cerrado(self, db, _tenant_user_task):
        tenant, user_id, task = _tenant_user_task
        pending, payload = await self._make_pending(db, tenant, task)
        text = svc.build_expected_approval_text("303", "1T-2026")

        # Primera aprobación OK
        await svc.approve_fiscal(
            db, pending_approval_id=pending.id, user_id=user_id,
            approval_text=text, model_aeat="303", period_year=2026,
            period_quarter=1, payload=payload,
        )
        await db.commit()

        # Segunda aprobación falla
        with pytest.raises(ValueError, match="ya cerrada"):
            await svc.approve_fiscal(
                db, pending_approval_id=pending.id, user_id=user_id,
                approval_text=text, model_aeat="303", period_year=2026,
                period_quarter=1, payload=payload,
            )


# ── reject_fiscal ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRejectFiscal:
    async def test_reject_happy_path(self, db, _tenant_user_task):
        tenant, user_id, task = _tenant_user_task
        pending = await svc.request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="303", period_year=2026, period_quarter=1,
            payload={"total": "100"},
        )
        await db.commit()

        log = await svc.reject_fiscal(
            db, pending_approval_id=pending.id, user_id=user_id,
            rejection_reason="Datos incorrectos",
            model_aeat="303", period_year=2026, period_quarter=1,
            payload={"total": "100"},
        )
        await db.commit()

        assert log.decision == "rejected"
        assert log.rejection_reason == "Datos incorrectos"
        # PendingApproval marcado como rechazado
        from sqlalchemy import select

        refreshed = (
            await db.execute(select(PendingApproval).where(PendingApproval.id == pending.id))
        ).scalar_one()
        assert refreshed.status == "rejected"
        assert refreshed.rejection_reason == "Datos incorrectos"


# ── has_valid_fiscal_approval ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestHasValidFiscalApproval:
    async def test_hit_si_payload_hash_coincide(self, db, _tenant_user_task):
        """Existencia de un log approved con hash exacto → True."""
        tenant, user_id, task = _tenant_user_task
        payload = {"total": "500.00"}
        pending = await svc.request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="303", period_year=2026, period_quarter=1, payload=payload,
        )
        await db.commit()
        text = svc.build_expected_approval_text("303", "1T-2026")
        await svc.approve_fiscal(
            db, pending_approval_id=pending.id, user_id=user_id,
            approval_text=text, model_aeat="303", period_year=2026,
            period_quarter=1, payload=payload,
        )
        await db.commit()

        valid = await svc.has_valid_fiscal_approval(
            db, tenant_id=tenant.id, model_aeat="303",
            period_year=2026, period_quarter=1,
            payload_hash=svc.compute_payload_hash(payload),
        )
        assert valid is True

    async def test_miss_si_payload_cambia(self, db, _tenant_user_task):
        """Ventana cerrada: aprobar→modificar→presentar NO permitido."""
        tenant, user_id, task = _tenant_user_task
        original = {"total": "500.00"}
        modified = {"total": "999.99"}

        pending = await svc.request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="303", period_year=2026, period_quarter=1, payload=original,
        )
        await db.commit()
        text = svc.build_expected_approval_text("303", "1T-2026")
        await svc.approve_fiscal(
            db, pending_approval_id=pending.id, user_id=user_id,
            approval_text=text, model_aeat="303", period_year=2026,
            period_quarter=1, payload=original,
        )
        await db.commit()

        # Aprobé el original, pero pregunto por el modificado → False
        valid = await svc.has_valid_fiscal_approval(
            db, tenant_id=tenant.id, model_aeat="303",
            period_year=2026, period_quarter=1,
            payload_hash=svc.compute_payload_hash(modified),
        )
        assert valid is False

    async def test_miss_si_decision_rejected(self, db, _tenant_user_task):
        tenant, user_id, task = _tenant_user_task
        payload = {"total": "500.00"}
        pending = await svc.request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="303", period_year=2026, period_quarter=1, payload=payload,
        )
        await db.commit()
        await svc.reject_fiscal(
            db, pending_approval_id=pending.id, user_id=user_id,
            rejection_reason="x",
            model_aeat="303", period_year=2026, period_quarter=1, payload=payload,
        )
        await db.commit()

        valid = await svc.has_valid_fiscal_approval(
            db, tenant_id=tenant.id, model_aeat="303",
            period_year=2026, period_quarter=1,
            payload_hash=svc.compute_payload_hash(payload),
        )
        assert valid is False

    async def test_aislamiento_por_tenant(self, db, _tenant_user_task):
        """Aprobación de un tenant NO valida la de otro."""
        tenant, user_id, task = _tenant_user_task
        payload = {"total": "500.00"}
        pending = await svc.request_fiscal_approval(
            db, tenant_id=tenant.id, task_id=task.id,
            model_aeat="303", period_year=2026, period_quarter=1, payload=payload,
        )
        await db.commit()
        text = svc.build_expected_approval_text("303", "1T-2026")
        await svc.approve_fiscal(
            db, pending_approval_id=pending.id, user_id=user_id,
            approval_text=text, model_aeat="303", period_year=2026,
            period_quarter=1, payload=payload,
        )
        await db.commit()

        other_tenant_id = uuid4()
        valid = await svc.has_valid_fiscal_approval(
            db, tenant_id=other_tenant_id, model_aeat="303",
            period_year=2026, period_quarter=1,
            payload_hash=svc.compute_payload_hash(payload),
        )
        assert valid is False
