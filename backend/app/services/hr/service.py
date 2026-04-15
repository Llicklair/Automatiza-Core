"""Servicio de dominio para RRHH.

Encapsula: CRUD empleados/nóminas, cálculo SS/IRPF, generación PDF,
documentos de empleado, finiquito, liquidación, registro de jornada.
"""

import logging
import os
import uuid as uuid_mod
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.base import AsyncSessionLocal
from app.db.models.models import Employee, Payroll, Tenant, TenantDocument
from app.services.event_bus import emit_event
from app.services.pdf import (
    generate_finiquito_pdf as _pdf_finiquito,
    generate_liquidacion_finiquito_pdf as _pdf_liquidacion,
    generate_payroll_pdf,
    generate_registro_jornada_pdf as _pdf_registro_jornada,
)
from app.services.state_machine import validate_transition
from app.services.template_service import get_default_theme

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")
)

# Tasas SS empleado 2024/2025 — Régimen General (trabajador)
_SS_CONTINGENCIAS = 0.0470
_SS_DESEMPLEO = 0.0155
_SS_FP = 0.0010
_SS_MEI = 0.0010


# ── Cálculo de nómina ────────────────────────────────────────────────────────


def calc_payroll(base_salary: float, irpf_rate: float) -> dict:
    """Calcula deducciones de SS e IRPF sobre el salario base mensual."""
    ss_cc = round(base_salary * _SS_CONTINGENCIAS, 2)
    ss_des = round(base_salary * _SS_DESEMPLEO, 2)
    ss_fp = round(base_salary * _SS_FP, 2)
    ss_mei = round(base_salary * _SS_MEI, 2)
    total_ss = round(ss_cc + ss_des + ss_fp + ss_mei, 2)
    irpf = round(base_salary * (irpf_rate / 100), 2)
    deductions = round(total_ss + irpf, 2)
    net = round(base_salary - deductions, 2)
    return {
        "ss_contingencias_comunes": ss_cc,
        "ss_desempleo": ss_des,
        "ss_formacion_profesional": ss_fp,
        "ss_mei": ss_mei,
        "total_ss": total_ss,
        "irpf": irpf,
        "deductions": deductions,
        "net_salary": net,
    }


# ── Employees CRUD ───────────────────────────────────────────────────────────


async def list_employees(tenant_id, db: AsyncSession) -> list[Employee]:
    result = await db.execute(
        select(Employee)
        .where(Employee.tenant_id == tenant_id)
        .order_by(desc(Employee.created_at))
    )
    return list(result.scalars().all())


async def create_employee(payload, tenant_id, db: AsyncSession) -> Employee:
    """Crea empleado y emite evento. Lanza SQLAlchemyError si falla."""
    emp = Employee(tenant_id=tenant_id, **payload.model_dump())
    db.add(emp)
    await db.commit()
    await db.refresh(emp)

    try:
        await emit_event(db, tenant_id, None, "employee_created", {
            "employee_id": str(emp.id), "name": emp.name,
        })
    except Exception:
        logger.warning("emit_event employee_created falló — no es crítico")

    return emp


async def get_employee(employee_id: UUID, tenant_id, db: AsyncSession) -> Employee | None:
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id, Employee.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def update_employee(employee_id: UUID, payload, tenant_id, db: AsyncSession) -> Employee | None:
    emp = await get_employee(employee_id, tenant_id, db)
    if not emp:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(emp, field, value)
    await db.commit()
    await db.refresh(emp)
    return emp


async def delete_employee(employee_id: UUID, tenant_id, db: AsyncSession) -> bool:
    emp = await get_employee(employee_id, tenant_id, db)
    if not emp:
        return False
    await db.delete(emp)
    await db.commit()
    return True


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
    """Crea nómina con cálculo automático de SS e IRPF. Lanza ValueError si falla."""
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
    """Calcula preview de nómina sin crear registro. Lanza ValueError."""
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
    """Aprueba nómina draft → approved. Lanza ValueError si no puede."""
    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
    )
    payroll = result.unique().scalar_one_or_none()
    if not payroll:
        raise ValueError("Nómina no encontrada")

    validate_transition("Payroll", payroll.status, "approved")

    payroll.status = "approved"
    await db.commit()
    await db.refresh(payroll)
    return payroll


async def update_payroll(payroll_id: UUID, payload, tenant_id, db: AsyncSession) -> Payroll | None:
    """Actualiza nómina draft. Recalcula si cambia base_salary."""
    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
    )
    payroll = result.unique().scalar_one_or_none()
    if not payroll:
        return None
    if payroll.status != "draft":
        raise ValueError("Solo se pueden editar nóminas en estado borrador")

    data = payload.model_dump(exclude_unset=True)

    if "base_salary" in data:
        emp = payroll.employee
        irpf_rate = float(emp.irpf_rate or 15.0) if emp else 15.0
        calc = calc_payroll(data["base_salary"], irpf_rate)
        data.update({
            "ss_contingencias_comunes": calc["ss_contingencias_comunes"],
            "ss_desempleo": calc["ss_desempleo"],
            "ss_formacion_profesional": calc["ss_formacion_profesional"],
            "ss_mei": calc["ss_mei"],
            "irpf": calc["irpf"],
            "deductions": round(calc["deductions"] + float(payroll.other_deductions or 0), 2),
            "net_salary": round(data["base_salary"] - calc["deductions"] - float(payroll.other_deductions or 0), 2),
        })

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
        raise ValueError("Solo se pueden eliminar nóminas en estado borrador")
    await db.delete(payroll)
    await db.commit()
    return True


# ── Payroll PDF ──────────────────────────────────────────────────────────────


def build_payroll_pdf(
    payroll: Payroll, theme_config: dict | None = None, tenant: Tenant | None = None,
) -> bytes:
    """Construye datos y llama al generador de PDF de nómina."""
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
    """Genera PDF de nómina, guarda en disco y registra como TenantDocument."""
    from app.db.base import AsyncSessionLocal

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
                parsed_content=f"Nómina de {payroll.employee.name if payroll.employee else 'empleado'} — Período {period}. Neto: {float(payroll.net_salary or 0):.2f}€",
            )
            db.add(doc)
            await db.commit()
            logger.info("[HR] PDF de nómina guardado: %s", filename)
    except Exception as e:
        logger.error("[HR] Error generando PDF de nómina: %s", e, exc_info=True)


# ── Employee documents ───────────────────────────────────────────────────────


async def list_employee_documents(employee_id: UUID, tenant_id, db: AsyncSession) -> list[dict]:
    category = f"empleado_{employee_id}"
    result = await db.execute(
        select(TenantDocument)
        .where(TenantDocument.tenant_id == tenant_id, TenantDocument.category == category)
        .order_by(desc(TenantDocument.created_at))
    )
    return [
        {
            "id": str(d.id), "file_name": d.file_name, "file_type": d.file_type,
            "file_size": d.file_size,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in result.scalars().all()
    ]


async def upload_employee_document(
    employee_id: UUID, filename: str, content: bytes, content_type: str | None,
    tenant_id, user_id, db: AsyncSession,
) -> dict:
    """Sube documento de empleado. Lanza ValueError si el empleado no existe."""
    emp = await get_employee(employee_id, tenant_id, db)
    if not emp:
        raise ValueError("Empleado no encontrado")

    folder = os.path.join(UPLOAD_DIR, "empleados", str(employee_id))
    os.makedirs(folder, exist_ok=True)
    safe_name = f"{uuid_mod.uuid4().hex[:8]}_{filename}"
    file_path = os.path.join(folder, safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    doc = TenantDocument(
        id=uuid_mod.uuid4(),
        tenant_id=tenant_id,
        uploaded_by=user_id,
        file_name=filename,
        file_type=content_type,
        file_path=file_path,
        file_size=len(content),
        category=f"empleado_{employee_id}",
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {
        "id": str(doc.id), "file_name": doc.file_name, "file_type": doc.file_type,
        "file_size": doc.file_size,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


async def get_employee_document(
    employee_id: UUID, doc_id: UUID, tenant_id, db: AsyncSession,
) -> TenantDocument | None:
    result = await db.execute(
        select(TenantDocument).where(
            TenantDocument.id == doc_id,
            TenantDocument.tenant_id == tenant_id,
            TenantDocument.category == f"empleado_{employee_id}",
        )
    )
    return result.scalar_one_or_none()


async def delete_employee_document(
    employee_id: UUID, doc_id: UUID, tenant_id, db: AsyncSession,
) -> bool:
    doc = await get_employee_document(employee_id, doc_id, tenant_id, db)
    if not doc:
        return False
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    await db.delete(doc)
    await db.commit()
    return True


# ── HR PDF helpers ───────────────────────────────────────────────────────────


async def download_payroll_pdf(
    payroll_id: UUID, tenant_id, db: AsyncSession,
) -> tuple[bytes, str]:
    """Genera PDF de nómina para descarga. Lanza ValueError si no existe."""
    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
    )
    payroll = result.unique().scalar_one_or_none()
    if not payroll:
        raise ValueError("Nómina no encontrada")

    theme_config = await get_default_theme(tenant_id, "payroll", db)
    tenant = await db.get(Tenant, tenant_id)

    pdf_bytes = build_payroll_pdf(payroll, theme_config, tenant=tenant)
    emp_name = payroll.employee.name.replace(" ", "_") if payroll.employee else "empleado"
    period = payroll.period_start.strftime("%Y-%m") if payroll.period_start else "periodo"
    filename = f"Nomina_{emp_name}_{period}.pdf"

    return pdf_bytes, filename


def read_document_file(doc: TenantDocument) -> tuple[bytes, str, str]:
    """Lee archivo de documento del disco. Lanza FileNotFoundError si no existe."""
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise FileNotFoundError("Documento no encontrado en disco")
    with open(doc.file_path, "rb") as f:
        content = f.read()
    media_type = doc.file_type or "application/octet-stream"
    filename = doc.file_name or "documento"
    return content, media_type, filename


async def load_employee_and_tenant(
    employee_id: UUID, tenant_id, db: AsyncSession,
) -> tuple[Employee, Tenant | None]:
    """Carga empleado y tenant. Lanza ValueError si no existe."""
    emp = await db.get(Employee, employee_id)
    if not emp or emp.tenant_id != tenant_id:
        raise ValueError("Empleado no encontrado")
    tenant = await db.get(Tenant, tenant_id)
    return emp, tenant


def generate_finiquito_pdf(emp: Employee, tenant: Tenant | None, payload) -> tuple[bytes, str]:
    finiquito_data = {
        "employee": {"name": emp.name, "nif": emp.nif or ""},
        "company": {
            "name": tenant.name if tenant else "",
            "nif": tenant.nif if tenant else "",
            "address": tenant.address if tenant else "",
        },
        "fecha_baja": payload.fecha_baja,
        "causa_baja": payload.causa_baja,
        "conceptos": [c.model_dump() for c in payload.conceptos],
        "total_percepciones": payload.total_percepciones,
        "total_deducciones": payload.total_deducciones,
        "liquido": payload.liquido,
        "fecha": datetime.now(UTC).isoformat(),
    }
    pdf_bytes = _pdf_finiquito(finiquito_data)
    filename = f"Finiquito_{emp.name.replace(' ', '_')}_{payload.fecha_baja[:10]}.pdf"
    return pdf_bytes, filename


def generate_liquidacion_pdf(emp: Employee, tenant: Tenant | None, payload) -> tuple[bytes, str]:
    liquidacion_data = {
        "employee": {
            "name": emp.name, "nif": emp.nif or "",
            "naf": getattr(emp, "numero_afiliacion_ss", "") or "",
            "fecha_alta": emp.join_date.isoformat() if emp.join_date else "",
            "categoria": getattr(emp, "categoria_profesional", "") or "",
        },
        "company": {
            "name": tenant.name if tenant else "",
            "nif": tenant.nif if tenant else "",
            "address": tenant.address if tenant else "",
        },
        "fecha_baja": payload.fecha_baja,
        "causa_baja": payload.causa_baja,
        "conceptos": [c.model_dump() for c in payload.conceptos],
        "total_devengos": payload.total_devengos,
        "total_deducciones": payload.total_deducciones,
        "liquido": payload.liquido,
        "fecha": datetime.now(UTC).isoformat(),
    }
    pdf_bytes = _pdf_liquidacion(liquidacion_data)
    filename = f"Liquidacion_{emp.name.replace(' ', '_')}_{payload.fecha_baja[:10]}.pdf"
    return pdf_bytes, filename


def generate_registro_jornada(emp: Employee, tenant: Tenant | None, payload) -> tuple[bytes, str]:
    registro_data = {
        "employee": {"name": emp.name, "nif": emp.nif or ""},
        "company": {
            "name": tenant.name if tenant else "",
            "nif": tenant.nif if tenant else "",
            "centro_trabajo": tenant.address if tenant else "",
        },
        "mes": payload.mes,
        "anio": payload.anio,
        "registros": [r.model_dump() for r in payload.registros],
        "total_horas_ordinarias": payload.total_horas_ordinarias,
        "total_horas_extras": payload.total_horas_extras,
    }
    pdf_bytes = _pdf_registro_jornada(registro_data)
    mes_str = f"{payload.anio}-{payload.mes:02d}"
    filename = f"Registro_Jornada_{emp.name.replace(' ', '_')}_{mes_str}.pdf"
    return pdf_bytes, filename
