"""Modo de remisión Verifactu por tenant (FAC.MODE)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import VerifactuConfig

logger = logging.getLogger("verifactu_mode")

VerifactuMode = Literal["voluntary", "no_remission"]
DEFAULT_MODE: VerifactuMode = "no_remission"


async def get_mode(db: AsyncSession, *, tenant_id: UUID) -> VerifactuMode:
    """Devuelve el modo del tenant. Sin fila → default `no_remission`."""
    result = await db.execute(select(VerifactuConfig.mode).where(VerifactuConfig.tenant_id == tenant_id))
    mode = result.scalar_one_or_none()
    return mode if mode else DEFAULT_MODE  # type: ignore[return-value]


async def get_config(db: AsyncSession, *, tenant_id: UUID) -> VerifactuConfig:
    """Devuelve la fila persistida o la crea con el default."""
    result = await db.execute(select(VerifactuConfig).where(VerifactuConfig.tenant_id == tenant_id))
    record = result.scalar_one_or_none()
    if record is not None:
        return record

    record = VerifactuConfig(tenant_id=tenant_id, mode=DEFAULT_MODE)
    db.add(record)
    await db.flush()
    return record


async def set_mode(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    mode: VerifactuMode,
    updated_by: UUID | None = None,
) -> VerifactuConfig:
    """Upsert del modo. Valida `mode`."""
    if mode not in ("voluntary", "no_remission"):
        raise ValueError(f"Modo inválido: {mode}")

    record = await get_config(db, tenant_id=tenant_id)
    record.mode = mode
    record.updated_by = updated_by
    record.updated_at = datetime.now(UTC)
    await db.flush()
    logger.info(
        "verifactu_mode.set tenant=%s mode=%s by=%s",
        tenant_id,
        mode,
        updated_by,
    )
    return record


async def should_remit(db: AsyncSession, *, tenant_id: UUID) -> bool:
    """Helper para el flujo de emisión: ¿se debe remitir esta factura?"""
    return (await get_mode(db, tenant_id=tenant_id)) == "voluntary"


def to_dict(record: VerifactuConfig) -> dict:
    return {
        "mode": record.mode,
        "updated_at": record.updated_at.isoformat(),
        "is_default": record.mode == DEFAULT_MODE,
    }
