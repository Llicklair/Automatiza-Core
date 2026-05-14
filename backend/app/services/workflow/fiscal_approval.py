"""Aprobación humana obligatoria para actos fiscales AEAT (SEC.APR).

Flujo:
    1. El sistema genera un borrador del modelo AEAT (303, 130, 347, 390, 111, 190).
    2. Se llama `request_fiscal_approval()` que crea un `PendingApproval` con
       risk_level=MANDATORY_HUMAN_FISCAL y devuelve su id.
    3. La UI muestra el borrador al usuario, captura el texto literal de
       confirmación ("CONFIRMO QUE HE REVISADO LOS DATOS Y ASUMO LA
       RESPONSABILIDAD..."), IP y user-agent.
    4. Se llama `approve_fiscal()` o `reject_fiscal()` que crea el registro
       append-only en `fiscal_approval_log` y marca el `PendingApproval` como
       approved/rejected.
    5. La presentación telemática solo se ejecuta si existe un
       `FiscalApprovalLog` con `decision="approved"` para el modelo+período.

Texto de aprobación obligatorio (configurable por idioma futuro):
    "Confirmo que he revisado los datos y asumo la responsabilidad de
     la presentación ante AEAT del modelo {model} para el período {period}."
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tasks import (
    FiscalApprovalLog,
    PendingApproval,
    RISK_LEVEL_MANDATORY_HUMAN_FISCAL,
    Task,
)


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """SHA-256 del payload del borrador serializado canónicamente."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_expected_approval_text(model_aeat: str, period: str) -> str:
    """Texto canónico que el usuario debe tipear literalmente para aprobar."""
    return (
        f"Confirmo que he revisado los datos y asumo la responsabilidad "
        f"de la presentacion ante AEAT del modelo {model_aeat} para el periodo {period}"
    )


async def request_fiscal_approval(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    task_id: UUID,
    model_aeat: str,
    period_year: int,
    period_quarter: int | None,
    payload: dict[str, Any],
    expires_in_days: int = 30,
) -> PendingApproval:
    """Crea una solicitud de aprobación humana para un modelo AEAT."""
    period = f"{period_quarter}T-{period_year}" if period_quarter else str(period_year)
    description = (
        f"Aprobación fiscal obligatoria — modelo {model_aeat} ({period}). "
        f"La presentación NO se realizará hasta que un usuario autorizado "
        f"confirme la revisión del borrador."
    )

    approval = PendingApproval(
        task_id=task_id,
        tenant_id=tenant_id,
        action_description=description,
        action_payload=payload,
        risk_level=RISK_LEVEL_MANDATORY_HUMAN_FISCAL,
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        status="pending",
    )
    db.add(approval)
    await db.flush()
    return approval


def _validate_approval_text(provided: str, expected: str) -> bool:
    """Comparación insensible a acentos y mayúsculas — el cliente puede
    escribir sin acentos en teclado típico."""
    def _normalize(s: str) -> str:
        return (
            s.strip()
            .lower()
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
            .replace("ñ", "n")
        )

    return _normalize(provided) == _normalize(expected)


async def approve_fiscal(
    db: AsyncSession,
    *,
    pending_approval_id: UUID,
    user_id: UUID,
    approval_text: str,
    model_aeat: str,
    period_year: int,
    period_quarter: int | None,
    payload: dict[str, Any],
    pdf_path: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> FiscalApprovalLog:
    """Crea el registro append-only de aprobación fiscal.

    Verifica que el `approval_text` provisto coincide con el texto canónico
    esperado (ignorando acentos y mayúsculas). Lanza `ValueError` si no.
    """
    period = f"{period_quarter}T-{period_year}" if period_quarter else str(period_year)
    expected = build_expected_approval_text(model_aeat, period)
    if not _validate_approval_text(approval_text, expected):
        raise ValueError(
            "Texto de aprobación no coincide. Debe escribir literalmente: "
            f"'{expected}'"
        )

    # Marcar el PendingApproval como aprobado
    result = await db.execute(
        select(PendingApproval).where(PendingApproval.id == pending_approval_id)
    )
    pending = result.scalar_one_or_none()
    if pending is None:
        raise LookupError(f"PendingApproval {pending_approval_id} no encontrado")
    if pending.status != "pending":
        raise ValueError(f"Aprobación ya cerrada (status={pending.status})")

    pending.status = "approved"
    pending.approved_by = user_id
    pending.approved_at = datetime.now(timezone.utc)

    # Crear el log append-only
    log = FiscalApprovalLog(
        tenant_id=pending.tenant_id,
        user_id=user_id,
        pending_approval_id=pending_approval_id,
        model_aeat=model_aeat,
        period_quarter=period_quarter,
        period_year=period_year,
        payload_hash=compute_payload_hash(payload),
        pdf_path=pdf_path,
        approval_text=approval_text,
        decision="approved",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    await db.flush()
    return log


async def reject_fiscal(
    db: AsyncSession,
    *,
    pending_approval_id: UUID,
    user_id: UUID,
    rejection_reason: str,
    model_aeat: str,
    period_year: int,
    period_quarter: int | None,
    payload: dict[str, Any],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> FiscalApprovalLog:
    """Registra un rechazo append-only sin marcar el modelo como presentable."""
    result = await db.execute(
        select(PendingApproval).where(PendingApproval.id == pending_approval_id)
    )
    pending = result.scalar_one_or_none()
    if pending is None:
        raise LookupError(f"PendingApproval {pending_approval_id} no encontrado")
    if pending.status != "pending":
        raise ValueError(f"Aprobación ya cerrada (status={pending.status})")

    pending.status = "rejected"
    pending.rejection_reason = rejection_reason

    log = FiscalApprovalLog(
        tenant_id=pending.tenant_id,
        user_id=user_id,
        pending_approval_id=pending_approval_id,
        model_aeat=model_aeat,
        period_quarter=period_quarter,
        period_year=period_year,
        payload_hash=compute_payload_hash(payload),
        approval_text="(rechazado)",
        decision="rejected",
        rejection_reason=rejection_reason,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    await db.flush()
    return log


async def has_valid_fiscal_approval(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    model_aeat: str,
    period_year: int,
    period_quarter: int | None,
    payload_hash: str,
) -> bool:
    """Verifica si existe una aprobación válida (approved) para el borrador exacto.

    El `payload_hash` debe coincidir — si el borrador cambió tras la aprobación,
    se requiere re-aprobar. Esto cierra la ventana "aprobar, modificar, presentar".
    """
    result = await db.execute(
        select(FiscalApprovalLog)
        .where(
            FiscalApprovalLog.tenant_id == tenant_id,
            FiscalApprovalLog.model_aeat == model_aeat,
            FiscalApprovalLog.period_year == period_year,
            FiscalApprovalLog.period_quarter == period_quarter,
            FiscalApprovalLog.payload_hash == payload_hash,
            FiscalApprovalLog.decision == "approved",
        )
        .order_by(desc(FiscalApprovalLog.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
