"""Payroll CRUD, calculation preview, PDF generation and persistence."""

import logging
import os
import uuid as uuid_mod
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.base import AsyncSessionLocal
from app.db.models.models import Payroll, Tenant, TenantDocument
from app.services.pdf import generate_payroll_pdf
from app.services.state_machine import validate_transition
from app.services.template_service import get_default_theme

logger = logging.getLogger(__name__)


# ── Payrolls CRUD ────────────────────────────────────────────────────────────


async def list_payrolls(tenant_id, db: AsyncSession) -> list[Payroll]:
    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.tenant_id == tenant_id)
        .order_by(desc(Payroll.period_start))
    )
    return list(result.scalars().all())


async def create_payroll(payload, tenant_id, db: AsyncSession) -> Payroll:
    new_payroll = Payroll(tenant_id=tenant_id, **payload.model_dump())
    db.add(new_payroll)
    await db.commit()
    await db.refresh(new_payroll)
    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.id == new_payroll.id, Payroll.tenant_id == tenant_id)
    )
    return result.unique().scalar_one()


async def create_payroll_auto(payload, tenant_id, db: AsyncSession) -> Payroll:
    """Crea nomina con calculo automatico de SS e IRPF. Lanza ValueError si falla."""
    from app.services.hr.service import calc_payroll, get_employee

    emp = await get_employee(payload.employee_id, tenant_id, db)
    if not emp:
        raise ValueError("Empleado no encontrado")

    base = float(payload.base_salary or emp.base_salary or 0)
    if base <= 0:
        raise ValueError("El salario base debe ser mayor que 0")

    irpf_rate = float(emp.irpf_rate or 15.0)
    calc = calc_payroll(base, irpf_rate)

    new_payroll = Payroll(
        tenant_id=tenant_id,
        employee_id=payload.employee_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        issue_date=payload.issue_date or datetime.now(UTC),
        base_salary=base,
        ss_contingencias_comunes=calc["ss_contingencias_comunes"],
        ss_desempleo=calc["ss_desempleo"],
        ss_formacion_profesional=calc["ss_formacion_profesional"],
        ss_mei=calc["ss_mei"],
        irpf=calc["irpf"],
        other_deductions=0.0,
        deductions=calc["deductions"],
        net_salary=calc["net_salary"],
        status=payload.status,
    )
    db.add(new_payroll)
    await db.commit()

    result = await db.execute(
        select(Payroll).options(joinedload(Payroll.employee)).where(Payroll.id == new_payroll.id)
    )
    return result.unique().scalar_one()


async def preview_payroll(employee_id: UUID, tenant_id, db: AsyncSession) -> dict:
    """Calcula preview de nomina sin crear registro. Lanza ValueError."""
    from app.services.hr.service import calc_payroll, get_employee

    emp = await get_employee(employee_id, tenant_id, db)
    if not emp:
        raise ValueError("Empleado no encontrado")
    if not emp.base_salary:
        raise ValueError("El empleado no tiene salario base configurado")

    base = float(emp.base_salary)
    irpf_rate = float(emp.irpf_rate or 15.0)
    calc = calc_payroll(base, irpf_rate)
    return {"employee_id": employee_id, "base_salary": base, "irpf_rate_applied": irpf_rate, **calc}


async def approve_payroll(payroll_id: UUID, tenant_id, user_id, db: AsyncSession) -> Payroll:
    """Aprueba nomina draft -> approved. Lanza ValueError si no puede."""
    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
    )
    payroll = result.unique().scalar_one_or_none()
    if not payroll:
        raise ValueError("Nomina no encontrada")

    validate_transition("Payroll", payroll.status, "approved")

    payroll.status = "approved"
    await db.commit()
    await db.refresh(payroll)
    return payroll


async def update_payroll(payroll_id: UUID, payload, tenant_id, db: AsyncSession) -> Payroll | None:
    """Actualiza nomina draft. Recalcula si cambia base_salary."""
    from app.services.hr.service import calc_payroll

    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
    )
    payroll = result.unique().scalar_one_or_none()
    if not payroll:
        return None
    if payroll.status != "draft":
        raise ValueError("Solo se pueden editar nominas en estado borrador")

    data = payload.model_dump(exclude_unset=True)

    if "base_salary" in data:
        emp = payroll.employee
        irpf_rate = float(emp.irpf_rate or 15.0) if emp else 15.0
        calc = calc_payroll(data["base_salary"], irpf_rate)
        data.update(
            {
                "ss_contingencias_comunes": calc["ss_contingencias_comunes"],
                "ss_desempleo": calc["ss_desempleo"],
                "ss_formacion_profesional": calc["ss_formacion_profesional"],
                "ss_mei": calc["ss_mei"],
                "irpf": calc["irpf"],
                "deductions": round(calc["deductions"] + float(payroll.other_deductions or 0), 2),
                "net_salary": round(
                    data["base_salary"] - calc["deductions"] - float(payroll.other_deductions or 0),
                    2,
                ),
            }
        )

    if "other_deductions" in data and "base_salary" not in data:
        base = float(payroll.base_salary)
        emp = payroll.employee
        irpf_rate = float(emp.irpf_rate or 15.0) if emp else 15.0
        calc = calc_payroll(base, irpf_rate)
        data["deductions"] = round(calc["deductions"] + data["other_deductions"], 2)
        data["net_salary"] = round(base - data["deductions"], 2)

    for field, value in data.items():
        setattr(payroll, field, value)
    await db.commit()

    result = await db.execute(
        select(Payroll).options(joinedload(Payroll.employee)).where(Payroll.id == payroll_id)
    )
    return result.unique().scalar_one()


async def delete_payroll(payroll_id: UUID, tenant_id, db: AsyncSession) -> bool:
    result = await db.execute(
        select(Payroll).where(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
    )
    payroll = result.scalar_one_or_none()
    if not payroll:
        return False
    if payroll.status != "draft":
        raise ValueError("Solo se pueden eliminar nominas en estado borrador")
    await db.delete(payroll)
    await db.commit()
    return True


# ── Payroll PDF ──────────────────────────────────────────────────────────────


def build_payroll_pdf(
    payroll: Payroll,
    theme_config: dict | None = None,
    tenant: Tenant | None = None,
) -> bytes:
    """Construye datos y llama al generador de PDF de nomina."""
    emp = payroll.employee
    base = float(payroll.base_salary or 0)
    gross = float(getattr(payroll, "gross_salary", None) or base)
    irpf = float(payroll.irpf or 0)
    ss_cc = float(payroll.ss_contingencias_comunes or 0)
    ss_des = float(payroll.ss_desempleo or 0)
    ss_fp = float(payroll.ss_formacion_profesional or 0)
    ss_mei = float(payroll.ss_mei or 0)
    total_ss = round(ss_cc + ss_des + ss_fp + ss_mei, 2)
    other = float(payroll.other_deductions or 0)
    net = float(payroll.net_salary or 0)

    employee_data = {
        "name": emp.name if emp else "Empleado",
        "nif": emp.nif if emp else "",
        "position": emp.role if emp else "",
        "department": emp.department if emp else "",
        "numero_afiliacion_ss": getattr(emp, "numero_afiliacion_ss", "") or "" if emp else "",
        "categoria_profesional": getattr(emp, "categoria_profesional", "") or "" if emp else "",
        "grupo_cotizacion": getattr(emp, "grupo_cotizacion", "") or "" if emp else "",
        "tipo_contrato": getattr(emp, "tipo_contrato", "") or "" if emp else "",
        "convenio_colectivo": getattr(emp, "convenio_colectivo", "") or "" if emp else "",
    }
    company_data = {
        "name": tenant.name if tenant else "Mi Empresa S.L.",
        "nif": tenant.nif if tenant else "",
        "address": tenant.address if tenant else "",
    }
    payroll_data = {
        "employee": employee_data,
        "company": company_data,
        "period_start": payroll.period_start.isoformat() if payroll.period_start else "",
        "period_end": payroll.period_end.isoformat() if payroll.period_end else "",
        "issue_date": (payroll.issue_date or datetime.now(UTC)).isoformat(),
        "base_salary": base,
        "gross_salary": gross,
        "ss_contingencias_comunes": ss_cc,
        "ss_desempleo": ss_des,
        "ss_formacion_profesional": ss_fp,
        "ss_mei": ss_mei,
        "ss_employee": total_ss,
        "irpf": irpf,
        "pct_irpf": float(getattr(payroll, "pct_irpf", 0) or 0),
        "other_deductions": other,
        "net_salary": net,
        "devengos_json": getattr(payroll, "devengos_json", None),
        "cuotas_empresa_json": getattr(payroll, "cuotas_empresa_json", None),
        "base_cotizacion_cc": float(getattr(payroll, "base_cotizacion_cc", 0) or 0) or None,
        "base_irpf": float(getattr(payroll, "base_irpf", 0) or 0) or None,
    }
    return generate_payroll_pdf(payroll_data, theme_config)


async def generate_and_save_payroll_pdf(payroll_id: str, tenant_id: str, user_id: str):
    """Genera PDF de nomina, guarda en disco y registra como TenantDocument."""
    from app.services.hr.service import UPLOAD_DIR

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Payroll)
                .options(joinedload(Payroll.employee))
                .where(Payroll.id == uuid_mod.UUID(payroll_id))
            )
            payroll = result.unique().scalar_one_or_none()
            if not payroll:
                return

            theme_config = await get_default_theme(uuid_mod.UUID(tenant_id), "payroll", db)
            tenant = await db.get(Tenant, uuid_mod.UUID(tenant_id))

            pdf_bytes = build_payroll_pdf(payroll, theme_config, tenant=tenant)

            emp_name = payroll.employee.name.replace(" ", "_") if payroll.employee else "empleado"
            period = payroll.period_start.strftime("%Y-%m") if payroll.period_start else "periodo"
            filename = f"Nomina_{emp_name}_{period}.pdf"

            nominas_dir = os.path.join(UPLOAD_DIR, "Nominas")
            os.makedirs(nominas_dir, exist_ok=True)
            file_path = os.path.join(nominas_dir, filename)
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)

            doc = TenantDocument(
                tenant_id=uuid_mod.UUID(tenant_id),
                uploaded_by=uuid_mod.UUID(user_id),
                file_name=filename,
                file_path=file_path,
                file_type="application/pdf",
                file_size=len(pdf_bytes),
                category="Nominas",
                status="processed",
                processed_at=datetime.now(UTC),
                parsed_content=f"Nomina de {payroll.employee.name if payroll.employee else 'empleado'} — Periodo {period}. Neto: {float(payroll.net_salary or 0):.2f}€",
            )
            db.add(doc)
            await db.commit()
            logger.info("[HR] PDF de nomina guardado: %s", filename)
    except Exception as e:
        logger.error("[HR] Error generando PDF de nomina: %s", e, exc_info=True)


async def download_payroll_pdf(
    payroll_id: UUID,
    tenant_id,
    db: AsyncSession,
) -> tuple[bytes, str]:
    """Genera PDF de nomina para descarga. Lanza ValueError si no existe."""
    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
    )
    payroll = result.unique().scalar_one_or_none()
    if not payroll:
        raise ValueError("Nomina no encontrada")

    theme_config = await get_default_theme(tenant_id, "payroll", db)
    tenant = await db.get(Tenant, tenant_id)

    pdf_bytes = build_payroll_pdf(payroll, theme_config, tenant=tenant)
    emp_name = payroll.employee.name.replace(" ", "_") if payroll.employee else "empleado"
    period = payroll.period_start.strftime("%Y-%m") if payroll.period_start else "periodo"
    filename = f"Nomina_{emp_name}_{period}.pdf"

    return pdf_bytes, filename
