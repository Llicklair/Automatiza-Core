"""Servicio del wizard onboarding focado (UI.ONB)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tenant import TenantOnboarding

logger = logging.getLogger("onboarding.wizard")

StepKey = Literal["company", "cert", "data", "use_case", "llm_config"]
STEP_KEYS: tuple[StepKey, ...] = ("company", "cert", "data", "use_case", "llm_config")


async def get_state(db: AsyncSession, *, tenant_id: UUID) -> TenantOnboarding:
    """Devuelve el registro de onboarding del tenant; lo crea si no existe."""
    result = await db.execute(
        select(TenantOnboarding).where(TenantOnboarding.tenant_id == tenant_id)
    )
    record = result.scalar_one_or_none()
    if record is not None:
        return record

    record = TenantOnboarding(tenant_id=tenant_id)
    db.add(record)
    await db.flush()
    return record


def _maybe_complete(record: TenantOnboarding) -> None:
    """Si los 5 pasos están a True, setea `completed_at` automáticamente."""
    all_done = (
        record.step_company
        and record.step_cert
        and record.step_data
        and record.step_use_case
        and record.step_llm_config
    )
    if all_done and record.completed_at is None:
        record.completed_at = datetime.now(UTC)


async def sync_llm_config_step(db: AsyncSession, *, tenant_id: UUID) -> TenantOnboarding:
    """Auto-marca `step_llm_config` desde la readiness REAL de IA del tenant.

    El paso BYOK refleja "el tenant tiene la IA configurada" — algo que ya
    sabemos sin que la UI lo marque: si `ai_ready` (clave de proveedor presente y
    activa, o Claude Code CLI disponible en dev) el paso pasa a True. Solo marca
    a True (nunca lo revierte), para no perder el progreso si la clave cambia.
    """
    record = await get_state(db, tenant_id=tenant_id)
    if record.step_llm_config:
        return record
    from app.services.tenant_service import get_llm_config

    cfg = await get_llm_config(db, tenant_id)
    if cfg.get("ai_ready"):
        record.step_llm_config = True
        record.updated_at = datetime.now(UTC)
        _maybe_complete(record)
        await db.flush()
    return record


async def set_step(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    step: StepKey,
    value: bool,
) -> TenantOnboarding:
    """Marca un paso como completado o pendiente."""
    if step not in STEP_KEYS:
        raise ValueError(f"Paso desconocido: {step}")
    record = await get_state(db, tenant_id=tenant_id)

    attr = f"step_{step}"
    setattr(record, attr, value)
    record.updated_at = datetime.now(UTC)
    _maybe_complete(record)
    await db.flush()
    return record


async def skip_to_end(db: AsyncSession, *, tenant_id: UUID) -> TenantOnboarding:
    """Marca el wizard como saltado por el usuario.

    Distinto de `completed`: el usuario dice "no quiero el tour" pero no
    necesariamente ha completado todos los pasos. La UI usa este flag para
    no volver a redirigir aquí desde el dashboard.
    """
    record = await get_state(db, tenant_id=tenant_id)
    if record.skipped_at is None:
        record.skipped_at = datetime.now(UTC)
        record.updated_at = datetime.now(UTC)
    await db.flush()
    return record


async def reset(db: AsyncSession, *, tenant_id: UUID) -> TenantOnboarding:
    """Reinicia todos los pasos. Útil para QA / re-onboarding manual."""
    record = await get_state(db, tenant_id=tenant_id)
    record.step_company = False
    record.step_cert = False
    record.step_data = False
    record.step_use_case = False
    record.step_llm_config = False
    record.completed_at = None
    record.skipped_at = None
    record.updated_at = datetime.now(UTC)
    await db.flush()
    return record


def to_dict(record: TenantOnboarding) -> dict:
    return {
        "step_company": record.step_company,
        "step_cert": record.step_cert,
        "step_data": record.step_data,
        "step_use_case": record.step_use_case,
        "step_llm_config": record.step_llm_config,
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        "skipped_at": record.skipped_at.isoformat() if record.skipped_at else None,
        "is_dismissed": record.completed_at is not None or record.skipped_at is not None,
    }
