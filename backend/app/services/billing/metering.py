"""Metered billing (OPS.OVR + OPS.CRON).

Política consensuada en Ronda 8 §41 + R.3 + R.4:

OPS.OVR (interacciones):
* `Solo` (39€/mes) — sin cap explícito de interacciones (uso responsable).
* `Pro` (65€/mes) — soft cap 500/mes:
    - 0-449: silencioso.
    - 450-499: banner suave "Has usado X de 500 interacciones este mes".
    - 500: banner amarillo + activación de overage 0,05€ + IVA por extra.
    - 1000 extras (1500 total): hard cap, requiere confirmación explícita.
    - **Nunca bloquea operaciones fiscales** (facturación, presentación AEAT).
* `Gestoria` (159€/mes) — sin cap (premium).

OPS.CRON (ejecuciones cron):
* `Pro`: 200/mes.
* `Gestoria`: 200 × N empresas activas hasta tope 2000/mes.
* Si se alcanza el cap, cron pausa hasta el mes siguiente.
* Las ejecuciones manuales (no cron) no cuentan — el usuario puede usar el agente.

Precio overage (en euros, sin IVA):
* `INTERACTION_OVERAGE_PRICE_EUR = 0.05`
* Banner: "0,05€ + IVA por interacción adicional (0,0605€ final)" — coherente con R.4.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.metering import CronExecutionUsage, InteractionUsage

# Constantes consensuadas
INTERACTION_SOFT_CAP_PRO = 500
INTERACTION_WARNING_THRESHOLD = 450
INTERACTION_HARD_CAP_EXTRA = 1000  # extras sobre el soft cap (total 1500)
INTERACTION_OVERAGE_PRICE_EUR = Decimal("0.05")
INTERACTION_OVERAGE_IVA_PCT = Decimal("21")

CRON_CAP_PRO_FLAT = 200
CRON_CAP_GESTORIA_PER_COMPANY = 200
CRON_CAP_GESTORIA_MAX = 2000

Tier = Literal["solo", "pro", "gestoria"]


@dataclass
class InteractionStatus:
    """Resultado de `record_interaction()`. La UI lo consume para mostrar banners."""

    count: int
    overage_count: int
    soft_cap: int | None
    warning: bool  # 450 ≤ count < 500 → banner suave
    overage_active: bool  # count ≥ 500
    hard_cap_reached: bool  # overage ≥ 1000 → requiere confirmación
    pending_overage_charge_eur: float  # importe a cobrar (sin IVA)


@dataclass
class CronCapStatus:
    """Resultado de `record_cron_execution()`."""

    count: int
    cap: int
    cap_reached: bool


def _current_period() -> tuple[int, int]:
    now = datetime.now(UTC)
    return now.year, now.month


async def _get_or_create_interaction_row(
    db: AsyncSession, tenant_id: UUID, year: int, month: int
) -> InteractionUsage:
    result = await db.execute(
        select(InteractionUsage).where(
            InteractionUsage.tenant_id == tenant_id,
            InteractionUsage.year == year,
            InteractionUsage.month == month,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = InteractionUsage(tenant_id=tenant_id, year=year, month=month)
        db.add(row)
        await db.flush()
    return row


async def _get_or_create_cron_row(
    db: AsyncSession, tenant_id: UUID, year: int, month: int
) -> CronExecutionUsage:
    result = await db.execute(
        select(CronExecutionUsage).where(
            CronExecutionUsage.tenant_id == tenant_id,
            CronExecutionUsage.year == year,
            CronExecutionUsage.month == month,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = CronExecutionUsage(tenant_id=tenant_id, year=year, month=month)
        db.add(row)
        await db.flush()
    return row


async def record_interaction(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    tier: Tier = "pro",
) -> InteractionStatus:
    """Incrementa el contador de interacciones del mes en curso y devuelve estado.

    El estado lleva los flags `warning`, `overage_active`, `hard_cap_reached`
    que la UI consume para mostrar el banner adecuado y bloquear acciones no
    fiscales si procede.

    OPS.OVR — `Solo` y `Gestoria` no tienen cap explícito; devuelven status
    sin warning/overage. Solo `Pro` cuenta para soft cap 500.
    """
    year, month = _current_period()
    row = await _get_or_create_interaction_row(db, tenant_id, year, month)
    row.count += 1
    row.last_recorded_at = datetime.now(UTC)

    # Tiers sin soft cap → status simple.
    if tier != "pro":
        await db.flush()
        return InteractionStatus(
            count=row.count,
            overage_count=0,
            soft_cap=None,
            warning=False,
            overage_active=False,
            hard_cap_reached=False,
            pending_overage_charge_eur=0.0,
        )

    soft_cap = INTERACTION_SOFT_CAP_PRO
    warning = INTERACTION_WARNING_THRESHOLD <= row.count < soft_cap
    overage_active = row.count >= soft_cap
    if overage_active:
        row.overage_count = row.count - soft_cap
    hard_cap_reached = row.overage_count >= INTERACTION_HARD_CAP_EXTRA

    pending_charge = (
        Decimal(row.overage_count) * INTERACTION_OVERAGE_PRICE_EUR
        if overage_active else Decimal("0")
    )
    await db.flush()

    return InteractionStatus(
        count=row.count,
        overage_count=row.overage_count,
        soft_cap=soft_cap,
        warning=warning,
        overage_active=overage_active,
        hard_cap_reached=hard_cap_reached,
        pending_overage_charge_eur=float(pending_charge),
    )


def compute_cron_cap(tier: Tier, active_companies: int = 1) -> int:
    """Calcula el cap de ejecuciones cron del mes según tier."""
    if tier == "pro":
        return CRON_CAP_PRO_FLAT
    if tier == "gestoria":
        return min(CRON_CAP_GESTORIA_PER_COMPANY * max(active_companies, 1), CRON_CAP_GESTORIA_MAX)
    # `solo`: cron no es feature de tier solo
    return 0


async def record_cron_execution(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    tier: Tier = "pro",
    active_companies: int = 1,
) -> CronCapStatus:
    """Incrementa contador de cron del mes y devuelve si se llegó al cap.

    Si `cap_reached == True`, el caller debe pausar la ejecución del cron y
    no incrementar más este mes. La ejecución manual del workflow por parte
    del usuario sigue permitida (no llama a este helper).
    """
    year, month = _current_period()
    row = await _get_or_create_cron_row(db, tenant_id, year, month)
    cap = compute_cron_cap(tier, active_companies)

    if row.count >= cap:
        # Ya estaba en el cap antes de esta ejecución
        return CronCapStatus(count=row.count, cap=cap, cap_reached=True)

    row.count += 1
    row.last_recorded_at = datetime.now(UTC)
    await db.flush()
    return CronCapStatus(count=row.count, cap=cap, cap_reached=row.count >= cap)
