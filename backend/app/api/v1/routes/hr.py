import logging
import os
import uuid as uuid_mod
from datetime import UTC, datetime
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)

from app.api.v1.schemas.hr import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    FiniquitoRequest,
    LiquidacionRequest,
    PayrollCalculateResponse,
    PayrollCreate,
    PayrollResponse,
    PayrollSimpleCreate,
    PayrollUpdate,
    RegistroJornadaRequest,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Employee, Payroll, Tenant, TenantDocument, User

router = APIRouter(prefix="/hr", tags=["hr"])

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads"))


# ─── Employees ───────────────────────────────────────────────────────────────

@router.get("/employees", response_model=list[EmployeeResponse])
@limiter.limit("30/minute")
async def list_employees(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Employee).where(Employee.tenant_id == current_user.tenant_id).order_by(desc(Employee.created_at))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_employee(
    request: Request,
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
@limiter.limit("30/minute")
async def update_employee(
    request: Request,
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
@limiter.limit("30/minute")
async def delete_employee(
    request: Request,
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

# Tasas SS empleado 2024/2025 — Régimen General (trabajador)
# Fuente: Seguridad Social / Orden PCM vigente
_SS_CONTINGENCIAS = 0.0470   # 4,70%
_SS_DESEMPLEO     = 0.0155   # 1,55% (contrato indefinido tipo general)
_SS_FP            = 0.0010   # 0,10%
_SS_MEI           = 0.0010   # 0,10% MEI trabajador (empresa: 0,50%; total: 0,58% — no 0,12%)


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
@limiter.limit("30/minute")
async def preview_payroll(
    request: Request,
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
@limiter.limit("30/minute")
async def generate_payroll_auto(
    request: Request,
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
@limiter.limit("30/minute")
async def list_payrolls(
    request: Request,
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
@limiter.limit("30/minute")
async def generate_payroll(
    request: Request,
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
@limiter.limit("30/minute")
async def approve_payroll(
    request: Request,
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
    from app.services.state_machine import InvalidTransitionError, validate_transition
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
@limiter.limit("30/minute")
async def update_payroll(
    request: Request,
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
@limiter.limit("30/minute")
async def delete_payroll(
    request: Request,
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
@limiter.limit("30/minute")
async def download_payroll_pdf(
    request: Request,
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

    from app.api.v1.routes.templates import get_default_theme
    theme_config = await get_default_theme(current_user.tenant_id, "payroll", db)

    tenant = await db.get(Tenant, current_user.tenant_id)
    pdf_bytes = _build_payroll_pdf(payroll, theme_config, tenant=tenant)
    emp_name = payroll.employee.name.replace(" ", "_") if payroll.employee else "empleado"
    period = payroll.period_start.strftime("%Y-%m") if payroll.period_start else "periodo"
    filename = f"Nomina_{emp_name}_{period}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Documentos de empleado ──────────────────────────────────────────────────

@router.get("/employees/{employee_id}/documents")
async def list_employee_documents(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = f"empleado_{employee_id}"
    result = await db.execute(
        select(TenantDocument)
        .where(TenantDocument.tenant_id == current_user.tenant_id, TenantDocument.category == category)
        .order_by(desc(TenantDocument.created_at))
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "file_name": d.file_name,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@router.post("/employees/{employee_id}/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_employee_document_file(
    employee_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify employee belongs to tenant
    emp_result = await db.execute(
        select(Employee).where(Employee.id == employee_id, Employee.tenant_id == current_user.tenant_id)
    )
    if not emp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    folder = os.path.join(UPLOAD_DIR, "empleados", str(employee_id))
    os.makedirs(folder, exist_ok=True)

    safe_name = f"{uuid_mod.uuid4().hex[:8]}_{file.filename}"
    file_path = os.path.join(folder, safe_name)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = TenantDocument(
        id=uuid_mod.uuid4(),
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.id,
        file_name=file.filename,
        file_type=file.content_type,
        file_path=file_path,
        file_size=len(content),
        category=f"empleado_{employee_id}",
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {"id": str(doc.id), "file_name": doc.file_name, "file_type": doc.file_type, "file_size": doc.file_size, "created_at": doc.created_at.isoformat() if doc.created_at else None}


@router.get("/employees/{employee_id}/documents/{doc_id}/download")
async def download_employee_document(
    employee_id: UUID,
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TenantDocument).where(
            TenantDocument.id == doc_id,
            TenantDocument.tenant_id == current_user.tenant_id,
            TenantDocument.category == f"empleado_{employee_id}",
        )
    )
    doc = result.scalar_one_or_none()
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    with open(doc.file_path, "rb") as f:
        content = f.read()
    return Response(
        content=content,
        media_type=doc.file_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.file_name}"'},
    )


@router.delete("/employees/{employee_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee_document(
    employee_id: UUID,
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TenantDocument).where(
            TenantDocument.id == doc_id,
            TenantDocument.tenant_id == current_user.tenant_id,
            TenantDocument.category == f"empleado_{employee_id}",
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    await db.delete(doc)
    await db.commit()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_payroll_pdf(
    payroll: Payroll,
    theme_config: dict | None = None,
    tenant: Tenant | None = None,
) -> bytes:
    """Construye los datos y llama al generador de PDF de nómina."""
    from app.services.pdf_service import generate_payroll_pdf

    emp = payroll.employee
    base = float(payroll.base_salary or 0)
    gross = float(getattr(payroll, 'gross_salary', None) or base)
    irpf = float(payroll.irpf or 0)
    ss_cc  = float(payroll.ss_contingencias_comunes or 0)
    ss_des = float(payroll.ss_desempleo or 0)
    ss_fp  = float(payroll.ss_formacion_profesional or 0)
    ss_mei = float(payroll.ss_mei or 0)
    total_ss = round(ss_cc + ss_des + ss_fp + ss_mei, 2)
    other = float(payroll.other_deductions or 0)
    net  = float(payroll.net_salary or 0)

    # Datos del empleado — todos los campos disponibles
    employee_data = {
        "name":       emp.name       if emp else "Empleado",
        "nif":        emp.nif        if emp else "",
        "position":   emp.role       if emp else "",
        "department": emp.department if emp else "",
        "numero_afiliacion_ss":   getattr(emp, 'numero_afiliacion_ss', '') or '' if emp else '',
        "categoria_profesional":  getattr(emp, 'categoria_profesional', '') or '' if emp else '',
        "grupo_cotizacion":       getattr(emp, 'grupo_cotizacion', '') or '' if emp else '',
        "tipo_contrato":          getattr(emp, 'tipo_contrato', '') or '' if emp else '',
        "convenio_colectivo":     getattr(emp, 'convenio_colectivo', '') or '' if emp else '',
    }

    # Datos de la empresa — del tenant real
    company_data = {
        "name":    tenant.name    if tenant else "Mi Empresa S.L.",
        "nif":     tenant.nif     if tenant else "",
        "address": tenant.address if tenant else "",
    }

    payroll_data = {
        "employee": employee_data,
        "company":  company_data,
        "period_start": payroll.period_start.isoformat() if payroll.period_start else "",
        "period_end":   payroll.period_end.isoformat()   if payroll.period_end   else "",
        "issue_date":   (payroll.issue_date or datetime.now(UTC)).isoformat(),
        "base_salary":  base,
        "gross_salary": gross,
        "ss_contingencias_comunes": ss_cc,
        "ss_desempleo":             ss_des,
        "ss_formacion_profesional": ss_fp,
        "ss_mei":                   ss_mei,
        "ss_employee":              total_ss,
        "irpf":                     irpf,
        "pct_irpf":       float(getattr(payroll, 'pct_irpf', 0) or 0),
        "other_deductions":         other,
        "net_salary":               net,
        "devengos_json":          getattr(payroll, 'devengos_json', None),
        "cuotas_empresa_json":    getattr(payroll, 'cuotas_empresa_json', None),
        "base_cotizacion_cc":     float(getattr(payroll, 'base_cotizacion_cc', 0) or 0) or None,
        "base_irpf":              float(getattr(payroll, 'base_irpf', 0) or 0) or None,
    }
    return generate_payroll_pdf(payroll_data, theme_config)


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

            from app.api.v1.routes.templates import get_default_theme
            theme_config = await get_default_theme(uuid_mod.UUID(tenant_id), "payroll", db)

            # Cargar datos del tenant para la cabecera del PDF
            tenant = await db.get(Tenant, uuid_mod.UUID(tenant_id))

            pdf_bytes = _build_payroll_pdf(payroll, theme_config, tenant=tenant)

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


# ─── Endpoints PDF: Finiquito / Liquidación / Registro de Jornada ─────────

async def _load_employee_and_tenant(
    employee_id: UUID, tenant_id: UUID, db: AsyncSession
) -> tuple[Employee, Tenant]:
    """Carga empleado y tenant, lanza 404 si no existe."""
    emp = await db.get(Employee, employee_id)
    if not emp or emp.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    tenant = await db.get(Tenant, tenant_id)
    return emp, tenant


@router.post("/documents/finiquito/pdf")
@limiter.limit("10/minute")
async def generate_finiquito_pdf_endpoint(
    request: Request,
    payload: FiniquitoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera PDF de finiquito para un empleado."""
    from app.services.pdf_service import generate_finiquito_pdf

    emp, tenant = await _load_employee_and_tenant(
        payload.employee_id, current_user.tenant_id, db)

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
    pdf_bytes = generate_finiquito_pdf(finiquito_data)

    filename = f"Finiquito_{emp.name.replace(' ', '_')}_{payload.fecha_baja[:10]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/documents/liquidacion-finiquito/pdf")
@limiter.limit("10/minute")
async def generate_liquidacion_finiquito_pdf_endpoint(
    request: Request,
    payload: LiquidacionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera PDF de documento de liquidación y finiquito."""
    from app.services.pdf_service import generate_liquidacion_finiquito_pdf

    emp, tenant = await _load_employee_and_tenant(
        payload.employee_id, current_user.tenant_id, db)

    liquidacion_data = {
        "employee": {
            "name": emp.name,
            "nif": emp.nif or "",
            "naf": getattr(emp, 'numero_afiliacion_ss', '') or '',
            "fecha_alta": emp.join_date.isoformat() if emp.join_date else '',
            "categoria": getattr(emp, 'categoria_profesional', '') or '',
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
    pdf_bytes = generate_liquidacion_finiquito_pdf(liquidacion_data)

    filename = f"Liquidacion_{emp.name.replace(' ', '_')}_{payload.fecha_baja[:10]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/documents/registro-jornada/pdf")
@limiter.limit("10/minute")
async def generate_registro_jornada_pdf_endpoint(
    request: Request,
    payload: RegistroJornadaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera PDF de registro mensual de jornada."""
    from app.services.pdf_service import generate_registro_jornada_pdf

    emp, tenant = await _load_employee_and_tenant(
        payload.employee_id, current_user.tenant_id, db)

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
    pdf_bytes = generate_registro_jornada_pdf(registro_data)

    mes_str = f"{payload.anio}-{payload.mes:02d}"
    filename = f"Registro_Jornada_{emp.name.replace(' ', '_')}_{mes_str}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
