"""Cashflow + delinquency + compliance RGPD endpoints."""

from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload as jl

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Invoice, Payroll, Tenant, User
from app.services.pdf_service import (
    generate_cashflow_report_pdf,
    generate_delinquency_report_pdf,
    generate_rgpd_registry_pdf,
)

router = APIRouter()


# ─── Informe de Tesorería (Cash Flow) ────────────────────────────────────────

@router.get("/cashflow")
async def generate_cashflow(
    start: str = Query(description="Fecha inicio YYYY-MM-DD"),
    end: str = Query(description="Fecha fin YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera PDF de informe de tesorería / cash flow."""
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD.")

    # Tenant
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant_obj = tenant_q.scalar_one_or_none()
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa"

    # Facturas emitidas pendientes (cobros previstos)
    issued_pending_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == current_user.tenant_id,
                Invoice.invoice_type == "issued",
                Invoice.status.in_(["draft", "pending"]),
            )
        )
    )
    issued_pending = issued_pending_q.scalars().all()

    # Facturas recibidas pendientes (pagos previstos)
    received_pending_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == current_user.tenant_id,
                Invoice.invoice_type == "received",
                Invoice.status.in_(["draft", "pending"]),
            )
        )
    )
    received_pending = received_pending_q.scalars().all()

    # Nóminas pendientes
    payroll_pending_q = await db.execute(
        select(Payroll).where(
            and_(
                Payroll.tenant_id == current_user.tenant_id,
                Payroll.status != "paid",
                func.date(Payroll.period_end) >= start_date,
                func.date(Payroll.period_end) <= end_date,
            )
        )
    )
    payrolls_pending = payroll_pending_q.scalars().all()

    total_collections = sum(float(i.amount_total or 0) for i in issued_pending)
    total_payments = sum(float(i.amount_total or 0) for i in received_pending) + \
                     sum(float(p.net_salary or 0) for p in payrolls_pending)

    # Group by month
    monthly_coll = defaultdict(float)
    monthly_pay = defaultdict(float)

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
    initial_balance = 0.0  # Could be enhanced with bank balance
    cumulative = initial_balance
    periods = []
    for m in all_months:
        c = round(monthly_coll.get(m, 0), 2)
        p = round(monthly_pay.get(m, 0), 2)
        cumulative += c - p
        periods.append({"label": m, "collections": c, "payments": p, "cumulative_balance": round(cumulative, 2)})

    # Pending receivables for detail
    recv_detail = []
    for inv in sorted(issued_pending, key=lambda x: float(x.amount_total or 0), reverse=True)[:10]:
        inv_q = await db.execute(select(Invoice).options(jl(Invoice.client)).where(Invoice.id == inv.id))
        inv_full = inv_q.unique().scalar_one()
        recv_detail.append({
            "client_name": inv_full.client.name if inv_full.client else "—",
            "invoice_number": inv_full.invoice_number or str(inv_full.id)[:8],
            "due_date": (inv_full.due_date or inv_full.date).isoformat() if (inv_full.due_date or inv_full.date) else "",
            "amount": float(inv_full.amount_total or 0),
        })

    data = {
        "company": {"name": company_name, "nif": tenant_obj.nif if tenant_obj else ""},
        "period_start": start,
        "period_end": end,
        "initial_balance": initial_balance,
        "total_collections": round(total_collections, 2),
        "total_payments": round(total_payments, 2),
        "final_balance": round(initial_balance + total_collections - total_payments, 2),
        "periods": periods,
        "pending_receivables": recv_detail,
    }

    pdf_bytes = generate_cashflow_report_pdf(data)
    file_name = f"Tesoreria_{start}_{end}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


# ─── Informe de Morosidad ───────────────────────────────────────────────────

@router.get("/delinquency")
async def generate_delinquency(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera PDF de informe de morosidad (facturas vencidas impagadas)."""
    today = date.today()

    # Tenant
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant_obj = tenant_q.scalar_one_or_none()
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa"

    # Facturas emitidas vencidas no pagadas
    overdue_q = await db.execute(
        select(Invoice)
        .options(jl(Invoice.client))
        .where(
            and_(
                Invoice.tenant_id == current_user.tenant_id,
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
    buckets = {"0-30": {"count": 0, "amount": 0.0}, "31-60": {"count": 0, "amount": 0.0},
               "61-90": {"count": 0, "amount": 0.0}, ">90": {"count": 0, "amount": 0.0}}

    detail_list = []
    client_totals: dict[str, float] = {}
    total_days = 0

    for inv in overdue_invoices:
        days = (today - inv.due_date.date() if hasattr(inv.due_date, 'date') else today - inv.due_date).days
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

        detail_list.append({
            "client_name": client_name,
            "invoice_number": inv.invoice_number or str(inv.id)[:8],
            "due_date": inv.due_date.isoformat() if inv.due_date else "",
            "days_overdue": days,
            "amount": amount,
            "collection_status": "Pendiente",
        })

    # Round bucket amounts
    for b in buckets.values():
        b["amount"] = round(b["amount"], 2)

    total_overdue = sum(float(inv.amount_total or 0) for inv in overdue_invoices)
    num_overdue = len(overdue_invoices)
    avg_days = total_days / num_overdue if num_overdue > 0 else 0
    worst_client = max(client_totals, key=client_totals.get) if client_totals else "—"

    data = {
        "company": {"name": company_name, "nif": tenant_obj.nif if tenant_obj else ""},
        "cutoff_date": today.isoformat(),
        "total_overdue": round(total_overdue, 2),
        "num_overdue": num_overdue,
        "avg_days_overdue": round(avg_days, 1),
        "worst_client": worst_client,
        "aging_buckets": buckets,
        "overdue_invoices": sorted(detail_list, key=lambda x: x["days_overdue"], reverse=True),
    }

    pdf_bytes = generate_delinquency_report_pdf(data)
    file_name = f"Morosidad_{today.isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


# ─── Compliance: Registro RGPD ──────────────────────────────────────────────

@router.get("/compliance/rgpd-registry")
async def generate_rgpd_registry(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera PDF del registro de actividades de tratamiento RGPD (Art. 30)."""
    # Tenant
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant_obj = tenant_q.scalar_one_or_none()
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa"
    company_nif = tenant_obj.nif if tenant_obj else "B00000000"

    # Actividades de tratamiento predefinidas para un ERP de PYME
    activities = [
        {
            "name": "Gestión de clientes y proveedores",
            "purpose": "Mantenimiento de la relación contractual, facturación, comunicaciones comerciales",
            "legal_basis": "Art. 6.1.b RGPD — Ejecución de contrato",
            "data_subjects": "Clientes, proveedores, representantes legales",
            "data_categories": "Nombre, NIF/CIF, dirección, email, teléfono, datos bancarios",
            "recipients": "AEAT (obligación fiscal), entidades bancarias",
            "international_transfers": "No se realizan",
            "retention_period": "Duración de la relación contractual + 6 años (Art. 30 Código de Comercio)",
            "security_measures": "Control de acceso por roles, cifrado en tránsito (TLS), copias de seguridad",
        },
        {
            "name": "Gestión de recursos humanos",
            "purpose": "Gestión laboral, nóminas, prevención de riesgos, formación",
            "legal_basis": "Art. 6.1.b RGPD — Ejecución de contrato laboral; Art. 6.1.c — Obligación legal",
            "data_subjects": "Empleados, candidatos",
            "data_categories": "Nombre, NIF, dirección, datos bancarios, nóminas, historial laboral",
            "recipients": "Seguridad Social, AEAT, mutua de accidentes",
            "international_transfers": "No se realizan",
            "retention_period": "Duración de la relación laboral + 4 años (prescripción laboral)",
            "security_measures": "Acceso restringido a RRHH, cifrado de nóminas, auditoría de accesos",
        },
        {
            "name": "Facturación y contabilidad",
            "purpose": "Emisión de facturas, gestión contable, cumplimiento fiscal",
            "legal_basis": "Art. 6.1.c RGPD — Obligación legal (Ley de IVA, Código de Comercio)",
            "data_subjects": "Clientes, proveedores",
            "data_categories": "Datos identificativos, NIF, importes, conceptos facturados",
            "recipients": "AEAT, asesores fiscales",
            "international_transfers": "No se realizan",
            "retention_period": "6 años (Art. 30 Código de Comercio)",
            "security_measures": "Registro de auditoría, backups cifrados, acceso por roles",
        },
        {
            "name": "Comunicaciones por correo electrónico",
            "purpose": "Gestión de comunicaciones comerciales y operativas con clientes",
            "legal_basis": "Art. 6.1.b RGPD — Ejecución de contrato; Art. 6.1.f — Interés legítimo",
            "data_subjects": "Clientes, contactos comerciales",
            "data_categories": "Nombre, email, contenido de comunicaciones",
            "recipients": "Proveedor de correo electrónico",
            "international_transfers": "Posibles transferencias a EEUU (Google/Microsoft) con cláusulas contractuales tipo",
            "retention_period": "Duración de la relación + 1 año",
            "security_measures": "Cifrado TLS, autenticación OAuth 2.0, acceso restringido",
        },
    ]

    data = {
        "company": {"name": company_name, "nif": company_nif, "address": ""},
        "dpo": None,
        "activities": activities,
    }

    pdf_bytes = generate_rgpd_registry_pdf(data)
    file_name = f"Registro_RGPD_{company_nif}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
