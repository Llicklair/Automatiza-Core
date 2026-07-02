"""Delinquency / aging bucket analysis logic.

Extracted from api/v1/routes/reports/specialized.py.
"""

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload as jl

from app.core.datetime_utils import local_today
from app.db.models.models import Invoice, Tenant


async def build_delinquency_data(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> dict:
    """Agrega datos de morosidad (facturas vencidas impagadas).

    Returns dict ready for PDF generation.
    """
    today = local_today()

    # Tenant
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant_obj = tenant_q.scalar_one_or_none()
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa"

    # Facturas emitidas vencidas no pagadas
    overdue_q = await db.execute(
        select(Invoice)
        .options(jl(Invoice.client))
        .where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == "issued",
                Invoice.status.notin_(["paid", "cancelled"]),
                Invoice.due_date.isnot(None),
                func.date(Invoice.due_date) < today,
            )
        )
        .order_by(Invoice.due_date)
    )
    overdue_invoices = overdue_q.unique().scalars().all()

    # Build aging buckets
    buckets = {
        "0-30": {"count": 0, "amount": 0.0},
        "31-60": {"count": 0, "amount": 0.0},
        "61-90": {"count": 0, "amount": 0.0},
        ">90": {"count": 0, "amount": 0.0},
    }

    detail_list = []
    client_totals: dict[str, float] = {}
    total_days = 0

    for inv in overdue_invoices:
        days = (today - inv.due_date.date() if hasattr(inv.due_date, "date") else today - inv.due_date).days
        amount = float(inv.amount_total or 0)

        if days <= 30:
            buckets["0-30"]["count"] += 1
            buckets["0-30"]["amount"] += amount
        elif days <= 60:
            buckets["31-60"]["count"] += 1
            buckets["31-60"]["amount"] += amount
        elif days <= 90:
            buckets["61-90"]["count"] += 1
            buckets["61-90"]["amount"] += amount
        else:
            buckets[">90"]["count"] += 1
            buckets[">90"]["amount"] += amount

        total_days += days
        client_name = inv.client.name if inv.client else "—"
        client_totals[client_name] = client_totals.get(client_name, 0) + amount

        detail_list.append(
            {
                "client_name": client_name,
                "invoice_number": inv.invoice_number or str(inv.id)[:8],
                "due_date": inv.due_date.isoformat() if inv.due_date else "",
                "days_overdue": days,
                "amount": amount,
                "collection_status": "Pendiente",
            }
        )

    # Round bucket amounts
    for b in buckets.values():
        b["amount"] = round(b["amount"], 2)

    total_overdue = sum(float(inv.amount_total or 0) for inv in overdue_invoices)
    num_overdue = len(overdue_invoices)
    avg_days = total_days / num_overdue if num_overdue > 0 else 0
    worst_client = max(client_totals, key=client_totals.get) if client_totals else "—"

    return {
        "company": {"name": company_name, "nif": tenant_obj.nif if tenant_obj else ""},
        "cutoff_date": today.isoformat(),
        "total_overdue": round(total_overdue, 2),
        "num_overdue": num_overdue,
        "avg_days_overdue": round(avg_days, 1),
        "worst_client": worst_client,
        "aging_buckets": buckets,
        "overdue_invoices": sorted(detail_list, key=lambda x: x["days_overdue"], reverse=True),
    }
