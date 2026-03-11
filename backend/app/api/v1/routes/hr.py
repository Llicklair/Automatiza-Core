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

from app.api.v1.schemas.hr import EmployeeCreate, EmployeeResponse, EmployeeUpdate, PayrollCreate, PayrollResponse
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
    irpf = round(base * 0.15, 2)
    ss   = round(base * 0.0635, 2)
    other = max(0.0, float(payroll.deductions or 0) - irpf - ss)
    net  = float(payroll.net_salary or 0)

    payroll_data = {
        "employee": {
            "name":       emp.name      if emp else "Empleado",
            "nif":        emp.nif       if emp else "—",
            "position":   emp.role      if emp else "—",
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
        "irpf":         irpf,
        "ss_employee":  ss,
        "other_deductions": other,
        "net_salary":   net,
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
            print(f"[HR] PDF de nómina guardado: {filename}")
    except Exception as e:
        print(f"[HR] Error generando PDF de nómina: {e}")
        import traceback; traceback.print_exc()
