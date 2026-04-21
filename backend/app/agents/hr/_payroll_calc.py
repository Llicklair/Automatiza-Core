"""HR agent — payroll calculation tools (individual + bulk)."""

import logging
from calendar import monthrange
from datetime import UTC, datetime
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select

from app.agents.hr._payroll_pdf import _generate_and_save_payroll_pdf
from app.db.base import AsyncSessionLocal
from app.db.models.models import Employee, Payroll

logger = logging.getLogger(__name__)


@tool
async def calculate_and_create_payroll(
    tenant_id: str, nif: str, month: int, year: int, deductions: float = 0.0
) -> str:
    """
    Calcula la nómina de UN empleado específico (por NIF), creándola en estado DRAFT.
    Args:
        tenant_id: ID del tenant
        nif: NIF del empleado
        month: Mes (1-12)
        year: Año (ej. 2025)
        deductions: Deducciones extra (ausencias, adelantos...)
    """
    if not (1 <= int(month) <= 12):
        return f"Error: mes inválido {month}. Debe estar entre 1 y 12."
    from datetime import date as _date

    current_year = _date.today().year
    if not (2000 <= int(year) <= current_year + 1):
        return f"Error: año inválido {year}. Debe estar entre 2000 y {current_year + 1}."
    if deductions < 0:
        return f"Error: las deducciones no pueden ser negativas (recibido: {deductions})."

    return await _create_payroll_async(tenant_id, nif, month, year, deductions)


async def _create_payroll_async(
    tenant_id: str, nif: str, month: int, year: int, deductions: float
) -> str:
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

            ss_cc = round(base_salary * 0.0470, 2)
            ss_des = round(base_salary * 0.0155, 2)
            ss_fp = round(base_salary * 0.0010, 2)
            ss_mei = round(base_salary * 0.0013, 2)
            irpf = round(base_salary * irpf_rate / 100, 2)
            total_ded = ss_cc + ss_des + ss_fp + ss_mei + irpf + deductions
            net_salary = max(0.0, base_salary - total_ded)

            last_day = monthrange(year, month)[1]
            start_date = datetime(year, month, 1, tzinfo=UTC)
            end_date = datetime(year, month, last_day, tzinfo=UTC)

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

        payroll_numbers = {
            "base_salary": base_salary, "ss_contingencias_comunes": ss_cc,
            "ss_desempleo": ss_des, "ss_formacion_profesional": ss_fp,
            "ss_mei": ss_mei, "irpf": irpf, "irpf_rate": irpf_rate,
            "other_deductions": deductions, "net_salary": net_salary,
        }
        document_id, pdf_err = await _generate_and_save_payroll_pdf(
            tenant_id, employee, payroll_numbers, start_date, end_date, month, year
        )
        if pdf_err:
            logger.warning("Error PDF RRHH: %s", pdf_err)

        try:
            from app.services.event_bus import emit_event
            async with AsyncSessionLocal() as db_ev:
                await emit_event(
                    db=db_ev, tenant_id=UUID(tenant_id), user_id=None,
                    event_name="payroll_created",
                    context={
                        "payroll_id": str(payroll.id), "employee_name": employee.name,
                        "employee_nif": employee.nif, "net_salary": float(net_salary),
                        "document_id": document_id,
                    },
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
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Employee).where(Employee.tenant_id == UUID(tenant_id)))
            employees = result.scalars().all()

        if not employees:
            return "No hay empleados registrados. Usa `create_employee` primero para dar de alta empleados antes de generar nóminas."

        last_day = monthrange(year, month)[1]
        start_date = datetime(year, month, 1, tzinfo=UTC)
        end_date = datetime(year, month, last_day, tzinfo=UTC)

        summary_lines = []
        async with AsyncSessionLocal() as db:
            for emp in employees:
                base_salary = float(emp.base_salary) if emp.base_salary else 0
                irpf_rate = float(emp.irpf_rate) if emp.irpf_rate is not None else 15.0

                ss_cc = round(base_salary * 0.0470, 2)
                ss_des = round(base_salary * 0.0155, 2)
                ss_fp = round(base_salary * 0.0010, 2)
                ss_mei = round(base_salary * 0.0013, 2)
                irpf = round(base_salary * irpf_rate / 100, 2)
                total_ded = ss_cc + ss_des + ss_fp + ss_mei + irpf
                net_salary = max(0.0, base_salary - total_ded)

                db.add(Payroll(
                    tenant_id=UUID(tenant_id),
                    employee_id=emp.id,
                    period_start=start_date,
                    period_end=end_date,
                    issue_date=datetime.now(UTC),
                    base_salary=base_salary,
                    ss_contingencias_comunes=ss_cc,
                    ss_desempleo=ss_des,
                    ss_formacion_profesional=ss_fp,
                    ss_mei=ss_mei,
                    irpf=irpf,
                    other_deductions=0,
                    deductions=total_ded,
                    net_salary=net_salary,
                    status="draft",
                ))

                payroll_numbers = {
                    "base_salary": base_salary, "ss_contingencias_comunes": ss_cc,
                    "ss_desempleo": ss_des, "ss_formacion_profesional": ss_fp,
                    "ss_mei": ss_mei, "irpf": irpf, "irpf_rate": irpf_rate,
                    "other_deductions": 0.0, "net_salary": net_salary,
                }
                _, pdf_err = await _generate_and_save_payroll_pdf(
                    tenant_id, emp, payroll_numbers, start_date, end_date, month, year
                )
                if pdf_err:
                    logger.warning("Error PDF nómina masiva para %s: %s", emp.name, pdf_err)

                summary_lines.append(
                    f"- {emp.name}: Bruto {base_salary:.2f}€ → Neto {net_salary:.2f}€"
                )

            await db.commit()

        try:
            from app.services.event_bus import emit_event
            async with AsyncSessionLocal() as db_ev:
                await emit_event(
                    db=db_ev, tenant_id=UUID(tenant_id), user_id=None,
                    event_name="payrolls_bulk_created",
                    context={"count": len(employees), "month": month, "year": year},
                )
        except Exception as e:
            logger.warning("Error al emitir evento payrolls_bulk_created para tenant %s: %s", tenant_id, e)

        return (
            f"Nóminas de {month}/{year} generadas en modo DRAFT para {len(employees)} empleados:\n"
            + "\n".join(summary_lines)
            + "\n\nIMPORTANTE: Las nóminas están en estado BORRADOR. "
            "El responsable debe revisarlas y aprobarlas desde RRHH > Nóminas."
        )
    except Exception as e:
        return f"Error al generar nóminas en bloque: {str(e)}"
