"""Cashflow + delinquency + compliance RGPD endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import local_today
from app.core.dependencies import get_current_user, get_tenant_or_404
from app.db.base import get_db
from app.db.models.models import Tenant, User
from app.services.pdf import (
    generate_cashflow_report_pdf,
    generate_delinquency_report_pdf,
    generate_rgpd_registry_pdf,
)
from app.services.reports import build_cashflow_data, build_delinquency_data

router = APIRouter()


# ─── Informe de Tesoreria (Cash Flow) ────────────────────────────────────────


@router.get("/cashflow")
async def generate_cashflow(
    start: str = Query(description="Fecha inicio YYYY-MM-DD"),
    end: str = Query(description="Fecha fin YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera PDF de informe de tesoreria / cash flow."""
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Formato de fecha invalido. Usa YYYY-MM-DD.") from exc

    data = await build_cashflow_data(db, current_user.tenant_id, start_date, end_date)
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
    data = await build_delinquency_data(db, current_user.tenant_id)
    pdf_bytes = generate_delinquency_report_pdf(data)
    file_name = f"Morosidad_{local_today().isoformat()}.pdf"
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
    tenant: Tenant = Depends(get_tenant_or_404),
):
    """Genera PDF del registro de actividades de tratamiento RGPD (Art. 30)."""
    company_name = tenant.name if tenant.name else "Mi Empresa"
    company_nif = tenant.nif if tenant.nif else "B00000000"

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
