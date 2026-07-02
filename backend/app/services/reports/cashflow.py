"""Cashflow / treasury analysis logic.

Extracted from api/v1/routes/reports/specialized.py.
"""

import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload as jl

from app.db.models.models import Invoice, Payroll, Tenant


async def build_cashflow_data(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> dict:
    """Agrega datos de tesoreria / cash flow.

    Returns dict ready for PDF generation.
    """
    # Tenant
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant_obj = tenant_q.scalar_one_or_none()
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa"

    # Facturas emitidas pendientes (cobros previstos) — eager-load client
    # para evitar N+1 en el bucle "recv_detail" más abajo.
    issued_pending_q = await db.execute(
        select(Invoice)
        .options(jl(Invoice.client))
        .where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == "issued",
                Invoice.status.in_(["draft", "pending"]),
            )
        )
    )
    issued_pending = issued_pending_q.unique().scalars().all()

    # Facturas recibidas pendientes (pagos previstos)
    received_pending_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == "received",
                Invoice.status.in_(["draft", "pending"]),
            )
        )
    )
    received_pending = received_pending_q.scalars().all()

    # Nominas pendientes
    payroll_pending_q = await db.execute(
        select(Payroll).where(
            and_(
                Payroll.tenant_id == tenant_id,
                Payroll.status != "paid",
                func.date(Payroll.period_end) >= start_date,
                func.date(Payroll.period_end) <= end_date,
            )
        )
    )
    payrolls_pending = payroll_pending_q.scalars().all()

    total_collections = sum(float(i.amount_total or 0) for i in issued_pending)
    total_payments = sum(float(i.amount_total or 0) for i in received_pending) + sum(
        float(p.net_salary or 0) for p in payrolls_pending
    )

    # Group by month
    monthly_coll: dict[str, float] = defaultdict(float)
    monthly_pay: dict[str, float] = defaultdict(float)

    for inv in issued_pending:
        d = inv.due_date or inv.date
        if d:
            key = d.strftime("%Y-%m")
            monthly_coll[key] += float(inv.amount_total or 0)

    for inv in received_pending:
        d = inv.due_date or inv.date
        if d:
            key = d.strftime("%Y-%m")
            monthly_pay[key] += float(inv.amount_total or 0)

    for p in payrolls_pending:
        key = p.period_end.strftime("%Y-%m") if p.period_end else ""
        if key:
            monthly_pay[key] += float(p.net_salary or 0)

    # Build periods
    all_months = sorted(set(list(monthly_coll.keys()) + list(monthly_pay.keys())))
    initial_balance = 0.0
    cumulative = initial_balance
    periods = []
    for m in all_months:
        c = round(monthly_coll.get(m, 0), 2)
        p = round(monthly_pay.get(m, 0), 2)
        cumulative += c - p
        periods.append(
            {
                "label": m,
                "collections": c,
                "payments": p,
                "cumulative_balance": round(cumulative, 2),
            }
        )

    # Pending receivables detail (client ya viene eager-loaded del outer query)
    recv_detail = [
        {
            "client_name": inv.client.name if inv.client else "—",
            "invoice_number": inv.invoice_number or str(inv.id)[:8],
            "due_date": (inv.due_date or inv.date).isoformat() if (inv.due_date or inv.date) else "",
            "amount": float(inv.amount_total or 0),
        }
        for inv in sorted(issued_pending, key=lambda x: float(x.amount_total or 0), reverse=True)[:10]
    ]

    return {
        "company": {"name": company_name, "nif": tenant_obj.nif if tenant_obj else ""},
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "initial_balance": initial_balance,
        "total_collections": round(total_collections, 2),
        "total_payments": round(total_payments, 2),
        "final_balance": round(initial_balance + total_collections - total_payments, 2),
        "periods": periods,
        "pending_receivables": recv_detail,
    }
