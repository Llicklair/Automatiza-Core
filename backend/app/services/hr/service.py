"""Servicio de dominio para RRHH.

Empleados CRUD + calculo de nomina viven aqui.
Sub-modulos: _payroll (nominas), _employee_docs (documentos), _special_docs (finiquito etc).
"""

import logging
import os
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Employee
from app.services.event_bus import emit_event

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))

# Tasas SS empleado 2024/2025 — Regimen General (trabajador)
_SS_CONTINGENCIAS = 0.0470
_SS_DESEMPLEO = 0.0155
_SS_FP = 0.0010
_SS_MEI = 0.0010


# ── Calculo de nomina ────────────────────────────────────────────────────────


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
        select(Employee).where(Employee.tenant_id == tenant_id).order_by(desc(Employee.created_at))
    )
    return list(result.scalars().all())


async def create_employee(payload, tenant_id, db: AsyncSession) -> Employee:
    """Crea empleado y emite evento. Lanza SQLAlchemyError si falla."""
    emp = Employee(tenant_id=tenant_id, **payload.model_dump())
    db.add(emp)
    await db.commit()
    await db.refresh(emp)

    try:
        await emit_event(
            db,
            tenant_id,
            None,
            "employee_created",
            {
                "employee_id": str(emp.id),
                "name": emp.name,
            },
        )
    except Exception:
        logger.warning("emit_event employee_created fallo — no es critico")

    return emp


async def get_employee(employee_id: UUID, tenant_id, db: AsyncSession) -> Employee | None:
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id, Employee.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def update_employee(
    employee_id: UUID, payload, tenant_id, db: AsyncSession
) -> Employee | None:
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


# ── Re-exports from sub-modules ─────────────────────────────────────────────
# Keep `svc.X` working for all callers without changing imports.

from app.services.hr._employee_docs import (  # noqa: E402, F401
    delete_employee_document,
    get_employee_document,
    list_employee_documents,
    read_document_file,
    upload_employee_document,
)
from app.services.hr._payroll import (  # noqa: E402, F401
    approve_payroll,
    build_payroll_pdf,
    create_payroll,
    create_payroll_auto,
    delete_payroll,
    download_payroll_pdf,
    generate_and_save_payroll_pdf,
    list_payrolls,
    preview_payroll,
    update_payroll,
)
from app.services.hr._special_docs import (  # noqa: E402, F401
    generate_finiquito_pdf,
    generate_liquidacion_pdf,
    generate_registro_jornada,
    load_employee_and_tenant,
)
