"""Servicio de política de autonomía por dominio (SEC.AUT).

Cada tenant configura el nivel de autonomía con el que sus agentes actúan
en cada dominio. Tres modos:

  - AUTO    — el agente actúa sin confirmación.
  - CONFIRM — el agente prepara la acción pero requiere clic humano.
  - MANUAL  — el agente solo sugiere; el usuario ejecuta manualmente.

Defaults consensuados en Ronda 30 §54:
  banking_write = MANUAL
  accounting    = CONFIRM
  marketing     = CONFIRM (beta)
  recruitment   = CONFIRM (beta)
  resto         = AUTO

La ausencia de fila en `autonomy_policy` equivale al default. La UI muestra
"Default (CONFIRM)" cuando la fila no existe; persiste solo al editar.

Los agentes consultan `check_autonomy(db, tenant_id, domain)` antes de
ejecutar tools que escriben (POST/PUT/DELETE), y se comportan según el
mode devuelto: AUTO ejecuta directo, CONFIRM crea `PendingApproval`,
MANUAL produce sugerencia sin tool call real.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tenant import AutonomyPolicy

logger = logging.getLogger("services.autonomy")

AutonomyMode = Literal["AUTO", "CONFIRM", "MANUAL"]

# Dominios reconocidos. Añadir un nuevo dominio requiere PR + actualizar
# la UI de Settings.
KNOWN_DOMAINS: frozenset[str] = frozenset({
    "banking_read",
    "banking_write",
    "accounting",
    "billing",
    "crm",
    "hr",
    "documents",
    "email",
    "marketing",
    "recruitment",
    "rag",
    "validators",
    "uploads",
})

# Defaults por dominio. Cualquier dominio no listado cae a AUTO.
DEFAULTS: dict[str, AutonomyMode] = {
    "banking_write": "MANUAL",
    "accounting": "CONFIRM",
    "marketing": "CONFIRM",
    "recruitment": "CONFIRM",
}


def default_mode(domain: str) -> AutonomyMode:
    return DEFAULTS.get(domain, "AUTO")


async def get_policy(
    db: AsyncSession, *, tenant_id: UUID, domain: str
) -> AutonomyMode:
    """Devuelve el mode efectivo (fila persistida o default del dominio)."""
    if domain not in KNOWN_DOMAINS:
        logger.warning("autonomy.get_policy: dominio desconocido %s", domain)
    result = await db.execute(
        select(AutonomyPolicy.mode).where(
            AutonomyPolicy.tenant_id == tenant_id,
            AutonomyPolicy.domain == domain,
        )
    )
    mode = result.scalar_one_or_none()
    if mode is None:
        return default_mode(domain)
    return mode  # type: ignore[return-value]


async def list_policies(
    db: AsyncSession, *, tenant_id: UUID
) -> dict[str, dict[str, str | bool]]:
    """Devuelve todas las policies efectivas del tenant.

    Para cada dominio conocido: `{mode, is_default}`. La UI usa
    `is_default` para mostrar el badge "(default)" hasta que el usuario
    sobrescriba.
    """
    result = await db.execute(
        select(AutonomyPolicy.domain, AutonomyPolicy.mode).where(
            AutonomyPolicy.tenant_id == tenant_id,
        )
    )
    persisted = {row[0]: row[1] for row in result.all()}

    out: dict[str, dict[str, str | bool]] = {}
    for domain in sorted(KNOWN_DOMAINS):
        if domain in persisted:
            out[domain] = {"mode": persisted[domain], "is_default": False}
        else:
            out[domain] = {"mode": default_mode(domain), "is_default": True}
    return out


async def set_policy(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    domain: str,
    mode: AutonomyMode,
    updated_by: UUID | None = None,
) -> AutonomyPolicy:
    """Upsert de la policy. Valida `domain` y `mode`."""
    if domain not in KNOWN_DOMAINS:
        raise ValueError(f"Dominio desconocido: {domain}")
    if mode not in ("AUTO", "CONFIRM", "MANUAL"):
        raise ValueError(f"Modo inválido: {mode}")

    result = await db.execute(
        select(AutonomyPolicy).where(
            AutonomyPolicy.tenant_id == tenant_id,
            AutonomyPolicy.domain == domain,
        )
    )
    record = result.scalar_one_or_none()

    if record is not None:
        record.mode = mode
        record.updated_by = updated_by
        record.updated_at = datetime.now(UTC)
    else:
        record = AutonomyPolicy(
            tenant_id=tenant_id,
            domain=domain,
            mode=mode,
            updated_by=updated_by,
        )
        db.add(record)
    await db.flush()
    return record


async def reset_policy(
    db: AsyncSession, *, tenant_id: UUID, domain: str
) -> None:
    """Elimina la fila persistida — vuelve al default del dominio."""
    if domain not in KNOWN_DOMAINS:
        raise ValueError(f"Dominio desconocido: {domain}")

    result = await db.execute(
        select(AutonomyPolicy).where(
            AutonomyPolicy.tenant_id == tenant_id,
            AutonomyPolicy.domain == domain,
        )
    )
    record = result.scalar_one_or_none()
    if record is not None:
        await db.delete(record)
        await db.flush()


async def check_autonomy(
    db: AsyncSession, *, tenant_id: UUID, domain: str
) -> AutonomyMode:
    """Helper para que los agentes consulten antes de ejecutar tools.

    Alias semántico de `get_policy` — facilita búsqueda por intención
    en código de agentes (`if mode := await check_autonomy(...): ...`).
    """
    return await get_policy(db, tenant_id=tenant_id, domain=domain)
