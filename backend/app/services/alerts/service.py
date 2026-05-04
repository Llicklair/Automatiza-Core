"""Alertas automáticas — checks periódicos sobre condiciones de negocio."""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import AsyncSessionLocal
from app.db.models.alerts import AlertLog
from app.db.models.auth import Tenant
from app.db.models.billing import Invoice
from app.db.models.hr import Payroll
from app.db.models.inventory import Product

logger = logging.getLogger(__name__)

_DEDUP_HOURS = 24


def _fmt(n) -> str:
    try:
        return f"{float(n):,.2f} €"
    except Exception:
        return str(n)


# ── Public API ───────────────────────────────────────────────────────────────

async def run_daily_alerts() -> None:
    """Entry point para el scheduler. Itera todos los tenants activos."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).where(Tenant.is_active.is_(True)))
        for tenant in result.scalars():
            try:
                count = await check_and_alert_tenant(db, tenant.id)
                if count:
                    logger.info("Alertas enviadas para tenant %s: %d", tenant.id, count)
            except Exception as exc:
                logger.error("Error en alertas para tenant %s: %s", tenant.id, exc)


async def check_and_alert_tenant(db: AsyncSession, tenant_id) -> int:
    """Ejecuta todos los checks y persiste alertas nuevas. Retorna nº de alertas nuevas."""
    candidates: list[dict] = []
    candidates += await _check_overdue_invoices(db, tenant_id)
    candidates += await _check_due_soon_invoices(db, tenant_id)
    candidates += await _check_low_stock(db, tenant_id)
    candidates += await _check_pending_payrolls(db, tenant_id)

    new_count = 0
    for alert in candidates:
        if await _is_duplicate(db, tenant_id, alert["type"], alert["entity_id"]):
            continue
        await _persist_and_notify(db, tenant_id, alert)
        new_count += 1

    return new_count


async def get_recent_alerts(db: AsyncSession, tenant_id, hours: int = 48) -> list[AlertLog]:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    rows = await db.execute(
        select(AlertLog)
        .where(AlertLog.tenant_id == tenant_id, AlertLog.sent_at > cutoff)
        .order_by(AlertLog.sent_at.desc())
        .limit(200)
    )
    return list(rows.scalars())


# ── Checks ───────────────────────────────────────────────────────────────────

async def _check_overdue_invoices(db: AsyncSession, tenant_id) -> list[dict]:
    now = datetime.now(UTC)
    rows = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.client))
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(["sent", "draft"]),
            Invoice.due_date.is_not(None),
            Invoice.due_date < now,
        )
    )
    return [
        {
            "type": "overdue_invoice",
            "entity_id": str(inv.id),
            "label": (
                f"Factura {inv.invoice_number or 'S/N'}"
                f" · {inv.client.name if inv.client else '—'}"
                f" · {_fmt(inv.amount_total)} VENCIDA"
            ),
            "severity": "error",
        }
        for inv in rows.scalars()
    ]


async def _check_due_soon_invoices(db: AsyncSession, tenant_id) -> list[dict]:
    now = datetime.now(UTC)
    horizon = now + timedelta(days=3)
    rows = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.client))
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(["sent", "draft"]),
            Invoice.due_date.is_not(None),
            Invoice.due_date > now,
            Invoice.due_date <= horizon,
        )
    )
    return [
        {
            "type": "due_soon_invoice",
            "entity_id": str(inv.id),
            "label": (
                f"Factura {inv.invoice_number or 'S/N'}"
                f" · {inv.client.name if inv.client else '—'}"
                f" · {_fmt(inv.amount_total)} vence en ≤3 días"
            ),
            "severity": "warning",
        }
        for inv in rows.scalars()
    ]


async def _check_low_stock(db: AsyncSession, tenant_id) -> list[dict]:
    rows = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.stock_min_alert > 0,
            Product.stock_quantity <= Product.stock_min_alert,
        )
    )
    return [
        {
            "type": "low_stock",
            "entity_id": str(p.id),
            "label": f"Stock bajo: {p.name} · {p.stock_quantity} uds (mín. {p.stock_min_alert})",
            "severity": "warning",
        }
        for p in rows.scalars()
    ]


async def _check_pending_payrolls(db: AsyncSession, tenant_id) -> list[dict]:
    rows = await db.execute(
        select(Payroll).where(
            Payroll.tenant_id == tenant_id,
            Payroll.status == "approved",
        )
    )
    return [
        {
            "type": "pending_payroll",
            "entity_id": str(p.id),
            "label": (
                f"Nómina aprobada pendiente de pago: "
                f"{p.period_start.strftime('%b %Y') if p.period_start else str(p.id)[:8]}"
            ),
            "severity": "info",
        }
        for p in rows.scalars()
    ]


# ── Dedup + persist ──────────────────────────────────────────────────────────

async def _is_duplicate(db: AsyncSession, tenant_id, alert_type: str, entity_id: str) -> bool:
    cutoff = datetime.now(UTC) - timedelta(hours=_DEDUP_HOURS)
    row = await db.execute(
        select(AlertLog.id).where(
            AlertLog.tenant_id == tenant_id,
            AlertLog.alert_type == alert_type,
            AlertLog.entity_id == entity_id,
            AlertLog.sent_at > cutoff,
        ).limit(1)
    )
    return row.scalar_one_or_none() is not None


async def _persist_and_notify(db: AsyncSession, tenant_id, alert: dict) -> None:
    log = AlertLog(
        tenant_id=tenant_id,
        alert_type=alert["type"],
        entity_id=alert["entity_id"],
        entity_label=alert["label"],
        severity=alert.get("severity", "warning"),
    )
    db.add(log)
    await db.flush()

    try:
        from app.api.ws.notifications import manager
        await manager.broadcast_to_tenant(str(tenant_id), {
            "type": "alert",
            "alert_type": alert["type"],
            "label": alert["label"],
            "severity": alert.get("severity", "warning"),
        })
        log.notified_ws = True
    except Exception as exc:
        logger.warning("WS broadcast failed for alert: %s", exc)

    await db.commit()
