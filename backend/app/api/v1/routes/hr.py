import logging
import os
import uuid as uuid_mod
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

from app.api.v1.schemas.hr import (
    EmployeeCreate, EmployeeResponse, EmployeeUpdate,
    PayrollCalculateResponse, PayrollCreate, PayrollResponse, PayrollSimpleCreate,
    PayrollUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Employee, Payroll, TenantDocument, User

router = APIRouter(prefix="/hr", tags=["hr"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")


# ─── Employees ───────────────────────────────────────────────────────────────

@router.get("/employees", response_model=list[EmployeeResponse])
async def list_employees(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Employee).where(Employee.tenant_id == current_user.tenant_id).order_by(desc(Employee.created_at))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_employee = Employee(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(new_employee)
    try:
        await db.commit()
        await db.refresh(new_employee)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error guardando empleado: %s", e)
        raise HTTPException(status_code=500, detail="Error al guardar el empleado")

    # Emitir evento para automatizaciones (no crítico)
    try:
        from app.services.event_bus import emit_event
        await emit_event(db, current_user.tenant_id, current_user.id, "employee_created",
                         {"employee_id": str(new_employee.id), "name": new_employee.name})
    except Exception:
        logger.warning("emit_event employee_created falló — no es crítico")

    return new_employee


@router.patch("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id, Employee.tenant_id == current_user.tenant_id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(emp, field, value)
    try:
        await db.commit()
        await db.refresh(emp)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error actualizando empleado %s: %s", employee_id, e)
        raise HTTPException(status_code=500, detail="Error al actualizar el empleado")
    return emp


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id, Employee.tenant_id == current_user.tenant_id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    try:
        await db.delete(emp)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error eliminando empleado %s: %s", employee_id, e)
        raise HTTPException(status_code=500, detail="Error al eliminar el empleado")


# ─── Payrolls ─────────────────────────────────────────────────────────────────

# Tasas SS empleado 2025 (Régimen General)
_SS_CONTINGENCIAS = 0.0470
_SS_DESEMPLEO     = 0.0155
_SS_FP            = 0.0010
_SS_MEI           = 0.0012


def _calc_payroll(base_salary: float, irpf_rate: float) -> dict:
    """Calcula deducciones de SS e IRPF sobre el salario base mensual."""
    ss_cc  = round(base_salary * _SS_CONTINGENCIAS, 2)
    ss_des = round(base_salary * _SS_DESEMPLEO, 2)
    ss_fp  = round(base_salary * _SS_FP, 2)
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


@router.get("/employees/{employee_id}/payroll/preview", response_model=PayrollCalculateResponse)
async def preview_payroll(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el cálculo de nómina para un empleado sin crear ningún registro."""
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id, Employee.tenant_id == current_user.tenant_id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if not emp.base_salary:
        raise HTTPException(status_code=400, detail="El empleado no tiene salario base configurado")

    base = float(emp.base_salary)
    irpf_rate = float(emp.irpf_rate or 15.0)
    calc = _calc_payroll(base, irpf_rate)

    return PayrollCalculateResponse(
        employee_id=employee_id,
        base_salary=base,
        irpf_rate_applied=irpf_rate,
        **calc,
    )


@router.post("/payrolls/auto", response_model=PayrollResponse, status_code=status.HTTP_201_CREATED)
async def generate_payroll_auto(
    payload: PayrollSimpleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea una nómina calculando automáticamente SS (tasas reales 2025) e IRPF."""
    emp_result = await db.execute(
        select(Employee).where(Employee.id == payload.employee_id, Employee.tenant_id == current_user.tenant_id)
    )
    emp = emp_result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    base = float(payload.base_salary or emp.base_salary or 0)
    if base <= 0:
        raise HTTPException(status_code=400, detail="El salario base debe ser mayor que 0")

    irpf_rate = float(emp.irpf_rate or 15.0)
    calc = _calc_payroll(base, irpf_rate)

    new_payroll = Payroll(
        tenant_id=current_user.tenant_id,
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
    try:
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error guardando nómina automática: %s", e)
        raise HTTPException(status_code=500, detail="Error al guardar la nómina")

    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.id == new_payroll.id)
    )
    return result.unique().scalar_one()


@router.get("/payrolls", response_model=list[PayrollResponse])
async def list_payrolls(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.tenant_id == current_user.tenant_id)
        .order_by(desc(Payroll.period_start))
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/payrolls", response_model=PayrollResponse, status_code=status.HTTP_201_CREATED)
async def generate_payroll(
    payload: PayrollCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crea una nómina en estado DRAFT y devuelve el objeto con la relación employee
    ya cargada para evitar accesos perezosos en el serializador (MissingGreenlet).
    """
    new_payroll = Payroll(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(new_payroll)
    await db.commit()
    await db.refresh(new_payroll)

    # Re-consultar con joinedload(Employee) para que la relación esté materializada
    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(
            Payroll.id == new_payroll.id,
            Payroll.tenant_id == current_user.tenant_id,
        )
    )
    payroll_with_employee = result.unique().scalar_one()
    return payroll_with_employee


@router.post("/payrolls/{payroll_id}/approve", response_model=PayrollResponse)
async def approve_payroll(
    payroll_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aprueba una nómina en estado DRAFT:
    1. Cambia el estado a 'sent'
    2. Genera el PDF de nómina
    3. Lo guarda en disco y registra como TenantDocument en carpeta 'Nóminas'
    """
    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.id == payroll_id, Payroll.tenant_id == current_user.tenant_id)
    )
    payroll = result.unique().scalar_one_or_none()
    if not payroll:
        raise HTTPException(status_code=404, detail="Nómina no encontrada")

    # ── State machine: valida que la transición draft → approved esté permitida ──
    from app.services.state_machine import validate_transition, InvalidTransitionError
    try:
        validate_transition("Payroll", payroll.status, "approved")
    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    payroll.status = "approved"
    await db.commit()
    await db.refresh(payroll)

    # Generar PDF en background
    background_tasks.add_task(
        _generate_and_save_payroll_pdf,
        payroll_id=str(payroll_id),
        tenant_id=str(current_user.tenant_id),
        user_id=str(current_user.id),
    )

    return payroll


@router.patch("/payrolls/{payroll_id}", response_model=PayrollResponse)
async def update_payroll(
    payroll_id: UUID,
    payload: PayrollUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza una nómina en estado draft. Si cambia base_salary, recalcula SS e IRPF."""
    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.id == payroll_id, Payroll.tenant_id == current_user.tenant_id)
    )
    payroll = result.unique().scalar_one_or_none()
    if not payroll:
        raise HTTPException(status_code=404, detail="Nómina no encontrada")
    if payroll.status != "draft":
        raise HTTPException(status_code=400, detail="Solo se pueden editar nóminas en estado borrador")

    data = payload.model_dump(exclude_unset=True)

    # Si cambia base_salary, recalcular deducciones
    if "base_salary" in data:
        emp = payroll.employee
        irpf_rate = float(emp.irpf_rate or 15.0) if emp else 15.0
        calc = _calc_payroll(data["base_salary"], irpf_rate)
        data.update({
            "ss_contingencias_comunes": calc["ss_contingencias_comunes"],
            "ss_desempleo": calc["ss_desempleo"],
            "ss_formacion_profesional": calc["ss_formacion_profesional"],
            "ss_mei": calc["ss_mei"],
            "irpf": calc["irpf"],
            "deductions": round(calc["deductions"] + float(payroll.other_deductions or 0), 2),
            "net_salary": round(data["base_salary"] - calc["deductions"] - float(payroll.other_deductions or 0), 2),
        })

    # Si cambia other_deductions (sin cambio de base_salary), recalcular totales
    if "other_deductions" in data and "base_salary" not in data:
        base = float(payroll.base_salary)
        emp = payroll.employee
        irpf_rate = float(emp.irpf_rate or 15.0) if emp else 15.0
        calc = _calc_payroll(base, irpf_rate)
        data["deductions"] = round(calc["deductions"] + data["other_deductions"], 2)
        data["net_salary"] = round(base - data["deductions"], 2)

    for field, value in data.items():
        setattr(payroll, field, value)

    try:
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error actualizando nómina %s: %s", payroll_id, e)
        raise HTTPException(status_code=500, detail="Error al actualizar la nómina")

    # Re-cargar con joinedload para la respuesta
    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.id == payroll_id)
    )
    return result.unique().scalar_one()


@router.delete("/payrolls/{payroll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payroll(
    payroll_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina una nómina en estado draft."""
    result = await db.execute(
        select(Payroll).where(Payroll.id == payroll_id, Payroll.tenant_id == current_user.tenant_id)
    )
    payroll = result.scalar_one_or_none()
    if not payroll:
        raise HTTPException(status_code=404, detail="Nómina no encontrada")
    if payroll.status != "draft":
        raise HTTPException(status_code=400, detail="Solo se pueden eliminar nóminas en estado borrador")
    try:
        await db.delete(payroll)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error eliminando nómina %s: %s", payroll_id, e)
        raise HTTPException(status_code=500, detail="Error al eliminar la nómina")


@router.get("/payrolls/{payroll_id}/pdf")
async def download_payroll_pdf(
    payroll_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera y retorna el PDF de una nómina directamente (sin guardar en disco)."""
    result = await db.execute(
        select(Payroll)
        .options(joinedload(Payroll.employee))
        .where(Payroll.id == payroll_id, Payroll.tenant_id == current_user.tenant_id)
    )
    payroll = result.unique().scalar_one_or_none()
    if not payroll:
        raise HTTPException(status_code=404, detail="Nómina no encontrada")

    pdf_bytes = _build_payroll_pdf(payroll)
    emp_name = payroll.employee.name.replace(" ", "_") if payroll.employee else "empleado"
    period = payroll.period_start.strftime("%Y-%m") if payroll.period_start else "periodo"
    filename = f"Nomina_{emp_name}_{period}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_payroll_pdf(payroll: Payroll) -> bytes:
    """Construye los datos y llama al generador de PDF de nómina."""
    from app.services.pdf_service import generate_payroll_pdf

    emp = payroll.employee
    base = float(payroll.base_salary or 0)
    irpf = float(payroll.irpf or 0)
    ss_cc  = float(payroll.ss_contingencias_comunes or 0)
    ss_des = float(payroll.ss_desempleo or 0)
    ss_fp  = float(payroll.ss_formacion_profesional or 0)
    ss_mei = float(payroll.ss_mei or 0)
    total_ss = round(ss_cc + ss_des + ss_fp + ss_mei, 2)
    other = float(payroll.other_deductions or 0)
    net  = float(payroll.net_salary or 0)

    payroll_data = {
        "employee": {
            "name":       emp.name       if emp else "Empleado",
            "nif":        emp.nif        if emp else "—",
            "position":   emp.role       if emp else "—",
            "department": emp.department if emp else "—",
        },
        "company": {
            "name":    "Mi Empresa S.L.",
            "nif":     "B00000000",
            "address": "Calle Principal, 1 · Madrid",
        },
        "period_start": payroll.period_start.isoformat() if payroll.period_start else "",
        "period_end":   payroll.period_end.isoformat()   if payroll.period_end   else "",
        "issue_date":   (payroll.issue_date or datetime.now(UTC)).isoformat(),
        "base_salary":  base,
        "ss_contingencias_comunes": ss_cc,
        "ss_desempleo":             ss_des,
        "ss_formacion_profesional": ss_fp,
        "ss_mei":                   ss_mei,
        "ss_employee":              total_ss,
        "irpf":                     irpf,
        "other_deductions":         other,
        "net_salary":               net,
    }
    return generate_payroll_pdf(payroll_data)


async def _generate_and_save_payroll_pdf(payroll_id: str, tenant_id: str, user_id: str):
    """Genera el PDF de la nómina, lo guarda en disco y lo registra como TenantDocument."""
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

            pdf_bytes = _build_payroll_pdf(payroll)

            emp_name = payroll.employee.name.replace(" ", "_") if payroll.employee else "empleado"
            period = payroll.period_start.strftime("%Y-%m") if payroll.period_start else "periodo"
            filename = f"Nomina_{emp_name}_{period}.pdf"

            # Guardar en disco en carpeta Nóminas
            nominas_dir = os.path.join(UPLOAD_DIR, "Nominas")
            os.makedirs(nominas_dir, exist_ok=True)
            file_path = os.path.join(nominas_dir, filename)
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)

            # Registrar en TenantDocument
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
