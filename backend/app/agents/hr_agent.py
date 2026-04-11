"""
Agente de RRHH — calcula y genera nóminas (draft) para empleados.
Puede generar la nómina de un empleado individual (por NIF) o para TODOS
los empleados activos del tenant en un mes dado.

Usa el LLM configurado en llm_factory (Gemini/Anthropic/OpenAI/Groq).
Las nóminas se crean en modo DRAFT y requieren aprobación humana.
Tras aprobación, se genera el PDF y se guarda como TenantDocument.
"""
import logging
from calendar import monthrange
from datetime import UTC, datetime
from uuid import UUID

logger = logging.getLogger(__name__)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
    update_existing_document,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge
from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.llm_factory import get_llm
from app.db.models.models import Employee, Payroll


def _get_llm():
    return get_llm(temperature=0)


# ─── Herramientas ─────────────────────────────────────────────────────────────

@tool
async def calculate_and_create_payroll(tenant_id: str, nif: str, month: int, year: int, deductions: float = 0.0) -> str:
    """
    Calcula la nómina de UN empleado específico (por NIF), creándola en estado DRAFT.
    Args:
        tenant_id: ID del tenant
        nif: NIF del empleado
        month: Mes (1-12)
        year: Año (ej. 2025)
        deductions: Deducciones extra (ausencias, adelantos...)
    """
    # Validate inputs
    if not (1 <= int(month) <= 12):
        return f"Error: mes inválido {month}. Debe estar entre 1 y 12."
    from datetime import date as _date
    current_year = _date.today().year
    if not (2000 <= int(year) <= current_year + 1):
        return f"Error: año inválido {year}. Debe estar entre 2000 y {current_year + 1}."
    if deductions < 0:
        return f"Error: las deducciones no pueden ser negativas (recibido: {deductions})."

    return await _create_payroll_async(tenant_id, nif, month, year, deductions)


async def _create_payroll_async(tenant_id: str, nif: str, month: int, year: int, deductions: float) -> str:
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Employee).where(
                    Employee.tenant_id == UUID(tenant_id),
                    Employee.nif == nif,
                )
            )
            employee = result.scalars().first()

            if not employee:
                return f"Error: Empleado con NIF {nif} no encontrado. Usa `create_employee` para darlo de alta primero."

            base_salary = float(employee.base_salary) if employee.base_salary else 0
            irpf_rate = float(employee.irpf_rate) if employee.irpf_rate is not None else 15.0

            # Desglose SS trabajador
            ss_cc = round(base_salary * 0.0470, 2)   # Contingencias comunes
            ss_des = round(base_salary * 0.0155, 2)   # Desempleo (indefinido)
            ss_fp = round(base_salary * 0.0010, 2)    # Formación profesional
            ss_mei = round(base_salary * 0.0013, 2)   # MEI
            irpf = round(base_salary * irpf_rate / 100, 2)
            total_ded = ss_cc + ss_des + ss_fp + ss_mei + irpf + deductions
            net_salary = max(0.0, base_salary - total_ded)

            last_day = monthrange(year, month)[1]
            start_date = datetime(year, month, 1, tzinfo=UTC)
            end_date   = datetime(year, month, last_day, tzinfo=UTC)

            payroll = Payroll(
                tenant_id=UUID(tenant_id),
                employee_id=employee.id,
                period_start=start_date,
                period_end=end_date,
                issue_date=datetime.now(UTC),
                base_salary=base_salary,
                ss_contingencias_comunes=ss_cc,
                ss_desempleo=ss_des,
                ss_formacion_profesional=ss_fp,
                ss_mei=ss_mei,
                irpf=irpf,
                other_deductions=deductions,
                deductions=total_ded,
                net_salary=net_salary,
                status="draft",
            )
            db.add(payroll)
            await db.commit()
            await db.refresh(payroll)

            # --- Generar PDF y Guardar en TenantDocument ---
            document_id = None
            try:
                import os

                from app.db.models.models import Tenant, TenantDocument
                from app.services.pdf_service import generate_payroll_pdf

                # Carga datos para el PDF
                async with AsyncSessionLocal() as db_pdf:
                    res_t = await db_pdf.execute(select(Tenant).where(Tenant.id == UUID(tenant_id)))
                    tenant_obj = res_t.scalar_one_or_none()
                    try:
                        from app.api.v1.routes.templates import get_default_theme
                        payroll_theme = await get_default_theme(UUID(tenant_id), "payroll", db_pdf)
                    except Exception as _e:
                        logger.warning("Error cargando tema nómina para tenant %s: %s", tenant_id, _e)
                        payroll_theme = None

                payroll_pdf_data = {
                    "employee": {
                        "name": employee.name,
                        "nif": employee.nif,
                        "position": employee.role or "Empleado",
                        "department": employee.department or "General",
                    },
                    "company": {
                        "name": tenant_obj.name if tenant_obj else "Empresa Cliente",
                        "nif": "B-00000000",
                        "address": "Calle Falsa 123, Madrid",
                    },
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "issue_date": datetime.now(UTC).isoformat(),
                    "base_salary": base_salary,
                    "ss_contingencias_comunes": ss_cc,
                    "ss_desempleo": ss_des,
                    "ss_formacion_profesional": ss_fp,
                    "ss_mei": ss_mei,
                    "irpf": irpf,
                    "irpf_rate": irpf_rate,
                    "other_deductions": deductions,
                    "net_salary": net_salary,
                }

                pdf_bytes = generate_payroll_pdf(payroll_pdf_data, payroll_theme)

                # Guardar en disco
                upload_dir = os.environ.get("UPLOAD_DIR", "/app/uploads")
                if not os.path.exists(upload_dir) and os.name == "nt":
                    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
                os.makedirs(upload_dir, exist_ok=True)

                file_name = f"Nomina_{employee.name.replace(' ', '_')}_{month}_{year}.pdf"
                file_path = os.path.join(upload_dir, file_name)
                with open(file_path, "wb") as f:
                    f.write(pdf_bytes)

                # Registrar en BD
                new_doc = TenantDocument(
                    tenant_id=UUID(tenant_id),
                    file_name=file_name,
                    file_path=file_path,
                    file_type="application/pdf",
                    file_size=len(pdf_bytes),
                    category="nominas",
                    status="completed"
                )
                async with AsyncSessionLocal() as db_doc:
                    db_doc.add(new_doc)
                    await db_doc.commit()
                    await db_doc.refresh(new_doc)
                    document_id = str(new_doc.id)
            except Exception as pdf_err:
                logger.warning(f"Error PDF RRHH: {pdf_err}")

            # --- Emitir Evento para Automatización ---
            try:
                from app.services.event_bus import emit_event
                async with AsyncSessionLocal() as db_ev:
                    await emit_event(
                        db=db_ev,
                        tenant_id=UUID(tenant_id),
                        user_id=None,
                        event_name="payroll_created",
                        context={
                            "payroll_id": str(payroll.id),
                            "employee_name": employee.name,
                            "employee_nif": employee.nif,
                            "net_salary": float(net_salary),
                            "document_id": document_id
                        }
                    )
            except Exception as e:
                logger.warning("Error al emitir evento payroll_created para empleado %s: %s", nif, e)

        return (
            f"Pre-nómina generada: {employee.name} (NIF: {nif}) | "
            f"Bruto: {base_salary:.2f}€ | SS(CC {ss_cc:.2f}+Des {ss_des:.2f}+FP {ss_fp:.2f}+MEI {ss_mei:.2f}) | "
            f"IRPF({irpf_rate:.1f}%): {irpf:.2f}€ | "
            f"Neto: {net_salary:.2f}€ | Estado: DRAFT | ID: {payroll.id} | "
            f"Documento generado: {document_id or 'Fallo al generar PDF'}"
        )
    except Exception as e:
        return f"Error procesando nómina de {nif}: {str(e)}"


@tool
async def generate_all_payrolls(tenant_id: str, month: int, year: int) -> str:
    """
    Genera las nóminas en borrador (DRAFT) para TODOS los empleados activos del tenant
    en un mes y año determinados. NO requiere NIF individual.
    Args:
        tenant_id: ID del tenant
        month: Mes (1-12)
        year: Año (ej. 2025)
    """
    return await _generate_all_payrolls_async(tenant_id, month, year)


async def _generate_all_payrolls_async(tenant_id: str, month: int, year: int) -> str:
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Employee).where(Employee.tenant_id == UUID(tenant_id))
            )
            employees = result.scalars().all()

            if not employees:
                return "No hay empleados registrados. Usa `create_employee` primero para dar de alta empleados antes de generar nóminas."

            last_day = monthrange(year, month)[1]
            start_date = datetime(year, month, 1, tzinfo=UTC)
            end_date   = datetime(year, month, last_day, tzinfo=UTC)

            summary_lines = []
            for emp in employees:
                base_salary = float(emp.base_salary) if emp.base_salary else 0
                irpf_rate = float(emp.irpf_rate) if emp.irpf_rate is not None else 15.0

                ss_cc = round(base_salary * 0.0470, 2)
                ss_des = round(base_salary * 0.0155, 2)
                ss_fp = round(base_salary * 0.0010, 2)
                ss_mei_val = round(base_salary * 0.0013, 2)
                irpf = round(base_salary * irpf_rate / 100, 2)
                total_ded = ss_cc + ss_des + ss_fp + ss_mei_val + irpf
                net_salary = max(0.0, base_salary - total_ded)

                payroll = Payroll(
                    tenant_id=UUID(tenant_id),
                    employee_id=emp.id,
                    period_start=start_date,
                    period_end=end_date,
                    issue_date=datetime.now(UTC),
                    base_salary=base_salary,
                    ss_contingencias_comunes=ss_cc,
                    ss_desempleo=ss_des,
                    ss_formacion_profesional=ss_fp,
                    ss_mei=ss_mei_val,
                    irpf=irpf,
                    other_deductions=0,
                    deductions=total_ded,
                    net_salary=net_salary,
                    status="draft",
                )
                db.add(payroll)

                # --- Generar PDF silencioso para cada nómina del bloque ---
                try:
                    import os

                    from app.db.models.models import TenantDocument
                    from app.services.pdf_service import generate_payroll_pdf

                    payroll_pdf_data = {
                        "employee": {
                            "name": emp.name,
                            "nif": emp.nif,
                            "position": emp.role or "Empleado",
                            "department": emp.department or "General",
                        },
                        "company": {"name": "Empresa Cliente", "nif": "B-00000000", "address": "Sede Central"},
                        "period_start": start_date.isoformat(),
                        "period_end": end_date.isoformat(),
                        "issue_date": datetime.now(UTC).isoformat(),
                        "base_salary": base_salary,
                        "ss_contingencias_comunes": ss_cc,
                        "ss_desempleo": ss_des,
                        "ss_formacion_profesional": ss_fp,
                        "ss_mei": ss_mei_val,
                        "irpf": irpf,
                        "irpf_rate": irpf_rate,
                        "other_deductions": 0.0,
                        "net_salary": net_salary,
                    }
                    try:
                        from app.api.v1.routes.templates import get_default_theme
                        _bulk_theme = await get_default_theme(UUID(tenant_id), "payroll", db)
                    except Exception as _e:
                        logger.warning("Error cargando tema nómina masiva para tenant %s: %s", tenant_id, _e)
                        _bulk_theme = None
                    pdf_bytes = generate_payroll_pdf(payroll_pdf_data, _bulk_theme)

                    file_name = f"Nomina_{emp.name.replace(' ', '_')}_{month}_{year}.pdf"
                    upload_dir = os.environ.get("UPLOAD_DIR", "/app/uploads")
                    if not os.path.exists(upload_dir) and os.name == "nt":
                        upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, file_name)
                    with open(file_path, "wb") as f: f.write(pdf_bytes)

                    new_doc = TenantDocument(
                        tenant_id=UUID(tenant_id),
                        file_name=file_name,
                        file_path=file_path,
                        file_type="application/pdf",
                        file_size=len(pdf_bytes),
                        category="nominas",
                        status="completed"
                    )
                    db.add(new_doc)
                except Exception as e:
                    logger.warning("Error al generar o guardar PDF de nómina para empleado %s: %s", emp.name, e)

                summary_lines.append(
                    f"- {emp.name}: Bruto {base_salary:.2f}€ → Neto {net_salary:.2f}€"
                )

            await db.commit()

            # --- Emitir Evento Global para el bloque ---
            try:
                from app.services.event_bus import emit_event
                async with AsyncSessionLocal() as db_ev:
                    await emit_event(
                        db=db_ev,
                        tenant_id=UUID(tenant_id),
                        user_id=None,
                        event_name="payrolls_bulk_created",
                        context={
                            "count": len(employees),
                            "month": month,
                            "year": year
                        }
                    )
            except Exception as e:
                logger.warning("Error al emitir evento payrolls_bulk_created para tenant %s: %s", tenant_id, e)


        summary = "\n".join(summary_lines)
        return (
            f"Nóminas de {month}/{year} generadas en modo DRAFT para {len(employees)} empleados:\n"
            f"{summary}\n\n"
            f"IMPORTANTE: Las nóminas están en estado BORRADOR. "
            f"El responsable debe revisarlas y aprobarlas desde RRHH > Nóminas."
        )
    except Exception as e:
        return f"Error al generar nóminas en bloque: {str(e)}"


@tool
async def list_employees(tenant_id: str) -> str:
    """
    Lista todos los empleados del tenant con su salario base y cargo.
    Útil antes de generar nóminas o para consultas de RRHH.
    Args:
        tenant_id: ID del tenant
    """
    return await _list_employees_async(tenant_id)


async def _list_employees_async(tenant_id: str) -> str:
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Employee).where(Employee.tenant_id == UUID(tenant_id))
            )
            employees = result.scalars().all()

        if not employees:
            return "No hay empleados registrados en el sistema."

        lines = [
            f"- {emp.name} | NIF: {emp.nif or 'N/A'} | "
            f"Cargo: {emp.role or 'N/A'} | Dpto: {emp.department or 'N/A'} | "
            f"Salario base: {float(emp.base_salary or 0):.2f}€"
            for emp in employees
        ]
        return f"Empleados ({len(employees)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error listando empleados: {str(e)}"


@tool
async def create_employee(
    tenant_id: str,
    name: str,
    nif: str,
    base_salary: float = 0.0,
    role: str = "",
    department: str = "",
    email: str = "",
    irpf_rate: float = 15.0,
) -> str:
    """
    Crea un nuevo empleado en el sistema de RRHH.

    Args:
        tenant_id: ID del tenant
        name: Nombre completo del empleado
        nif: NIF/DNI del empleado (9 caracteres)
        base_salary: Salario bruto mensual en euros (por defecto 0)
        role: Cargo o puesto (ej: 'Desarrollador', 'Comercial')
        department: Departamento (ej: 'Tecnología', 'Ventas')
        email: Email del empleado (opcional)
        irpf_rate: Tipo de retención IRPF en % (por defecto 15)
    """
    return await _create_employee_async(tenant_id, name, nif, base_salary, role, department, email, irpf_rate)


async def _create_employee_async(
    tenant_id: str, name: str, nif: str, base_salary: float,
    role: str, department: str, email: str, irpf_rate: float,
) -> str:
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal

    if not name.strip():
        return "Error: El nombre del empleado es obligatorio."
    if not nif.strip():
        return "Error: El NIF/DNI del empleado es obligatorio."

    try:
        async with AsyncSessionLocal() as db:
            # Verificar que no exista ya
            result = await db.execute(
                select(Employee).where(
                    Employee.tenant_id == UUID(tenant_id),
                    Employee.nif == nif.strip(),
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return f"Error: Ya existe un empleado con NIF {nif}: {existing.name} (ID: {existing.id})."

            emp = Employee(
                tenant_id=UUID(tenant_id),
                name=name.strip(),
                nif=nif.strip().upper(),
                email=email.strip() or None,
                base_salary=base_salary,
                role=role or None,
                department=department or None,
                irpf_rate=irpf_rate,
            )
            db.add(emp)
            await db.commit()
            await db.refresh(emp)

            # Emitir evento
            try:
                from app.services.event_bus import emit_event
                async with AsyncSessionLocal() as db_ev:
                    await emit_event(
                        db=db_ev,
                        tenant_id=UUID(tenant_id),
                        user_id=None,
                        event_name="employee_created",
                        context={
                            "employee_id": str(emp.id),
                            "name": emp.name,
                            "nif": emp.nif,
                        },
                    )
            except Exception:
                logger.debug("Failed to emit employee_created event for %s", emp.id, exc_info=True)

            return (
                f"Empleado creado correctamente.\n"
                f"Nombre: {emp.name}\n"
                f"NIF: {emp.nif}\n"
                f"Salario base: {base_salary:.2f}€/mes\n"
                f"Cargo: {role or 'No especificado'}\n"
                f"Departamento: {department or 'No especificado'}\n"
                f"IRPF: {irpf_rate}%\n"
                f"ID: {emp.id}"
            )
    except Exception as e:
        return f"Error creando empleado: {e}"


@tool
async def update_payroll(
    tenant_id: str, payroll_id: str,
    base_salary: str = "", deductions: str = "", notes: str = "",
) -> str:
    """
    Modifica una nómina en estado DRAFT (borrador). Recalcula SS, IRPF y neto automáticamente.
    Solo nóminas en borrador pueden editarse.

    Args:
        tenant_id: ID del tenant
        payroll_id: ID (UUID) de la nómina a modificar
        base_salary: Nuevo salario bruto mensual en euros (vacío = no cambiar)
        deductions: Nuevas deducciones extra en euros (vacío = no cambiar)
        notes: Notas internas (vacío = no cambiar)
    """
    return await _update_payroll_async(tenant_id, payroll_id, base_salary, deductions, notes)


async def _update_payroll_async(
    tenant_id: str, payroll_id: str,
    base_salary_str: str, deductions_str: str, notes: str,
) -> str:
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Payroll).where(
                    Payroll.tenant_id == UUID(tenant_id),
                    Payroll.id == UUID(payroll_id),
                )
            )
            payroll = result.scalar_one_or_none()
            if not payroll:
                return f"Error: Nómina con ID {payroll_id} no encontrada."

            if payroll.status != "draft":
                return f"Error: Solo se pueden editar nóminas en borrador. Estado actual: {payroll.status}."

            changes = []

            # Actualizar salario base
            base = float(payroll.base_salary)
            if base_salary_str.strip():
                try:
                    base = float(base_salary_str.strip().replace(",", "."))
                    payroll.base_salary = base
                    changes.append(f"bruto={base:.2f}€")
                except ValueError:
                    return f"Error: Salario base no válido: '{base_salary_str}'."

            # Actualizar deducciones extra
            extra_ded = float(payroll.other_deductions or 0)
            if deductions_str.strip():
                try:
                    extra_ded = float(deductions_str.strip().replace(",", "."))
                    payroll.other_deductions = extra_ded
                    changes.append(f"deducciones_extra={extra_ded:.2f}€")
                except ValueError:
                    return f"Error: Deducciones no válidas: '{deductions_str}'."

            # Recalcular todo
            irpf_rate = float(payroll.irpf / payroll.base_salary * 100) if payroll.base_salary and float(payroll.base_salary) > 0 else 15.0
            ss_cc = round(base * 0.0470, 2)
            ss_des = round(base * 0.0155, 2)
            ss_fp = round(base * 0.0010, 2)
            ss_mei = round(base * 0.0013, 2)
            irpf = round(base * irpf_rate / 100, 2)
            total_ded = ss_cc + ss_des + ss_fp + ss_mei + irpf + extra_ded
            net = max(0.0, base - total_ded)

            payroll.ss_contingencias_comunes = ss_cc
            payroll.ss_desempleo = ss_des
            payroll.ss_formacion_profesional = ss_fp
            payroll.ss_mei = ss_mei
            payroll.irpf = irpf
            payroll.deductions = total_ded
            payroll.net_salary = net

            if not changes:
                return "No se especificaron cambios. Indica qué quieres modificar (base_salary o deductions)."

            await db.commit()
            return (
                f"Nómina {payroll_id[:8]}... actualizada: {', '.join(changes)}.\n"
                f"Recalculado: Bruto {base:.2f}€ | SS {ss_cc + ss_des + ss_fp + ss_mei:.2f}€ | "
                f"IRPF {irpf:.2f}€ | Neto {net:.2f}€."
            )
    except Exception as e:
        return f"Error modificando nómina: {e}"


@tool
async def approve_payroll(tenant_id: str, payroll_id: str = "", approve_all: bool = False, month: int = 0, year: int = 0) -> str:
    """
    Aprueba nóminas en estado DRAFT, pasándolas a 'approved'.
    Puede aprobar una nómina individual por ID o todas las del mes.

    Args:
        tenant_id: ID del tenant
        payroll_id: ID (UUID) de una nómina específica (vacío si approve_all=True)
        approve_all: Si True, aprueba todas las nóminas DRAFT del mes/año indicado
        month: Mes (1-12), requerido si approve_all=True
        year: Año, requerido si approve_all=True
    """
    return await _approve_payroll_async(tenant_id, payroll_id, approve_all, month, year)


async def _approve_payroll_async(
    tenant_id: str, payroll_id: str, approve_all: bool, month: int, year: int,
) -> str:
    from sqlalchemy import and_, select

    from app.db.base import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            if approve_all:
                if not month or not year:
                    return "Error: Para aprobar todas las nóminas, indica mes y año."
                start_date = datetime(year, month, 1, tzinfo=UTC)
                last_day = monthrange(year, month)[1]
                end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)

                result = await db.execute(
                    select(Payroll).where(and_(
                        Payroll.tenant_id == UUID(tenant_id),
                        Payroll.status == "draft",
                        Payroll.period_start >= start_date,
                        Payroll.period_end <= end_date,
                    ))
                )
                payrolls = result.scalars().all()
                if not payrolls:
                    return f"No hay nóminas en borrador para {month}/{year}."

                for p in payrolls:
                    p.status = "approved"
                await db.commit()

                # Emitir evento
                try:
                    from app.services.event_bus import emit_event
                    async with AsyncSessionLocal() as db_ev:
                        await emit_event(
                            db=db_ev,
                            tenant_id=UUID(tenant_id),
                            user_id=None,
                            event_name="payrolls_approved",
                            context={"count": len(payrolls), "month": month, "year": year},
                        )
                except Exception:
                    logger.debug("Failed to emit payrolls_approved event", exc_info=True)

                return f"{len(payrolls)} nóminas de {month}/{year} aprobadas correctamente."
            else:
                if not payroll_id:
                    return "Error: Indica payroll_id o usa approve_all=True con mes y año."
                result = await db.execute(
                    select(Payroll).where(
                        Payroll.tenant_id == UUID(tenant_id),
                        Payroll.id == UUID(payroll_id),
                    )
                )
                payroll = result.scalar_one_or_none()
                if not payroll:
                    return f"Error: Nómina {payroll_id} no encontrada."
                if payroll.status != "draft":
                    return f"Error: La nómina ya está en estado '{payroll.status}', no se puede aprobar."

                payroll.status = "approved"
                await db.commit()
                return f"Nómina {payroll_id[:8]}... aprobada. Neto: {float(payroll.net_salary):.2f}€."
    except Exception as e:
        return f"Error aprobando nómina: {e}"


@tool
async def list_payrolls(tenant_id: str, month: int = 0, year: int = 0, status_filter: str = "all") -> str:
    """
    Lista las nóminas del tenant, opcionalmente filtradas por mes/año y estado.
    Útil para consultar nóminas generadas, ver estados, o preparar aprobaciones.

    Args:
        tenant_id: ID del tenant
        month: Mes (1-12), 0 = todos los meses
        year: Año, 0 = todos los años
        status_filter: Filtrar por estado ('draft', 'approved', 'all')
    """
    return await _list_payrolls_async(tenant_id, month, year, status_filter)


async def _list_payrolls_async(tenant_id: str, month: int, year: int, status_filter: str) -> str:
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            query = (
                select(Payroll, Employee)
                .join(Employee, Payroll.employee_id == Employee.id)
                .where(Payroll.tenant_id == UUID(tenant_id))
            )

            if month and year:
                start_date = datetime(year, month, 1, tzinfo=UTC)
                last_day = monthrange(year, month)[1]
                end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)
                query = query.where(
                    Payroll.period_start >= start_date,
                    Payroll.period_end <= end_date,
                )

            if status_filter != "all":
                query = query.where(Payroll.status == status_filter)

            query = query.order_by(Payroll.period_start.desc()).limit(30)
            result = await db.execute(query)
            rows = result.all()

            if not rows:
                return "No se encontraron nóminas con los filtros indicados."

            lines = []
            total_net = 0
            for payroll, emp in rows:
                total_net += float(payroll.net_salary)
                period = payroll.period_start.strftime("%m/%Y") if payroll.period_start else "?"
                lines.append(
                    f"- {emp.name} | {period} | Bruto: {float(payroll.base_salary):.2f}€ | "
                    f"Neto: {float(payroll.net_salary):.2f}€ | Estado: {payroll.status} | "
                    f"ID: {payroll.id}"
                )

            return (
                f"Nóminas ({len(rows)}):\n" + "\n".join(lines) +
                f"\n\nTotal neto: {total_net:.2f}€"
            )
    except Exception as e:
        return f"Error listando nóminas: {e}"


tools = [
    create_employee,
    calculate_and_create_payroll,
    generate_all_payrolls,
    list_employees,
    list_payrolls,
    update_payroll,
    approve_payroll,
    create_document,
    list_tenant_documents,
    update_existing_document,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
]


# ─── Nodos del grafo ──────────────────────────────────────────────────────────

async def hr_agent_node(state: AgentState):
    if "messages" not in state or not state["messages"]:
        sys_msg = SystemMessage(
            content=(
                "Eres el Agente de RRHH (Recursos Humanos) de la empresa automatizada. "
                "Tus capacidades:\n"
                "1. Crear empleados con `create_employee` (nombre, NIF, salario, cargo, departamento).\n"
                "2. Generar nóminas individuales con `calculate_and_create_payroll` (requiere NIF, mes, año).\n"
                "3. Generar TODAS las nóminas del mes con `generate_all_payrolls` (solo mes y año).\n"
                "4. Consultar empleados con `list_employees`.\n"
                "5. Consultar nóminas con `list_payrolls` — filtrar por mes/año y estado.\n"
                "6. Editar nómina con `update_payroll` — modificar salario base o deducciones (solo borradores).\n"
                "7. Aprobar nóminas con `approve_payroll` — individual por ID o masiva por mes/año.\n"
                "7. Crear documentos con `create_document`, leer con `get_document_content`.\n"
                "8. Memoria del tenant con `get_tenant_knowledge` y `upsert_tenant_knowledge`.\n"
                f"ID del Tenant actual: {state.get('tenant_id')}.\n"
                "Reglas:\n"
                "- Si el usuario pide crear un empleado que no existe, usa `create_employee` primero.\n"
                "- Si te piden nómina de alguien que no existe, CREA al empleado primero y luego genera la nómina.\n"
                "- Las nóminas se generan en estado DRAFT y requieren aprobación humana.\n"
                "- Para EDITAR una nómina, primero usa `list_payrolls` para obtener el ID.\n"
                "- Para APROBAR nóminas, usa `approve_payroll`. Puedes aprobar una o todas las del mes.\n"
                "- Si el usuario no especifica mes/año, usa el mes y año actuales.\n"
                "- Para generar todas las nóminas, usa `generate_all_payrolls` directamente sin pedir NIF.\n"
                "- Si el usuario pide nómina de un empleado específico, primero usa `list_employees` para "
                "obtener el NIF si no lo conoces.\n"
                "- Si se te pide exportar datos a CSV o texto, usa `create_document` con category='RRHH'."
            )
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    llm_with_tools = _get_llm().bind_tools(tools)
    response = await llm_with_tools.ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"hr_step_{datetime.now().timestamp()}",
        description="Procesando solicitud de RRHH...",
        status="completed",
        action_taken=(
            "Invocando herramientas de RRHH"
            if response.tool_calls
            else "Asistencia RRHH completada."
        ),
    )

    if "agent_results" not in state:
        state["agent_results"] = []

    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def hr_finalize_node(state: AgentState):
    """Cierra el flujo del agente de RRHH."""
    last_msg = state["messages"][-1]

    final_result = StepResult(
        step_id="hr_final",
        description="Agente RRHH ha finalizado.",
        status="completed",
        action_taken=(
            last_msg.content
            if isinstance(last_msg.content, str)
            else "Borradores generados localmente."
        ),
    )

    return {"status": "done", "agent_results": [final_result.model_dump()]}


# ─── Compilar grafo ───────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("hr_agent", hr_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", hr_finalize_node)

workflow.set_entry_point("hr_agent")
workflow.add_conditional_edges("hr_agent", tools_condition)
workflow.add_edge("tools", "hr_agent")

graph = workflow.compile()
