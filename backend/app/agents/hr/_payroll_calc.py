"""HR agent — payroll calculation tools (individual + bulk)."""

import logging
from calendar import monthrange
from datetime import UTC, datetime
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.agents.hr._payroll_pdf import _generate_and_save_payroll_pdf
from app.db.base import AsyncSessionLocal
from app.db.models.models import Employee, Payroll
from app.services.hr.queries import calc_payroll

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

            # Cálculo unificado: mismas tasas y tope de cotización que el resto
            # de la app (calc_payroll), evitando que la nómina creada por la IA
            # difiera de la creada vía API.
            calc = calc_payroll(base_salary, irpf_rate, year=year)
            ss_cc = calc["ss_contingencias_comunes"]
            ss_des = calc["ss_desempleo"]
            ss_fp = calc["ss_formacion_profesional"]
            ss_mei = calc["ss_mei"]
            irpf = calc["irpf"]
            total_ded = round(calc["deductions"] + deductions, 2)
            net_salary = max(0.0, round(base_salary - total_ded, 2))

            last_day = monthrange(year, month)[1]
            start_date = datetime(year, month, 1, tzinfo=UTC)
            end_date = datetime(year, month, last_day, tzinfo=UTC)

            # Guard de unicidad: ya existe nómina del mismo empleado para este
            # period_start? Si sí, devolver mensaje claro sin crear duplicado.
            # La BD también tiene UNIQUE(tenant_id, employee_id, period_start)
            # como segunda barrera (migración 0007_payroll_unique).
            existing = await db.execute(
                select(Payroll).where(
                    Payroll.tenant_id == UUID(tenant_id),
                    Payroll.employee_id == employee.id,
                    Payroll.period_start == start_date,
                )
            )
            existing_payroll = existing.scalar_one_or_none()
            if existing_payroll:
                return (
                    f"Ya existe una nómina para {employee.name} (NIF: {nif}) "
                    f"en {month:02d}/{year} (estado: {existing_payroll.status}, "
                    f"ID: {existing_payroll.id}). No se crea duplicado. "
                    f"Usa update_payroll si quieres modificarla."
                )

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
                cuota_solidaridad=calc["cuota_solidaridad"],
                irpf=irpf,
                other_deductions=deductions,
                deductions=total_ded,
                net_salary=net_salary,
                status="draft",
            )
            db.add(payroll)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                return (
                    f"Error: Ya existe una nómina para {employee.name} en "
                    f"{month:02d}/{year} (detectado por restricción de unicidad de BD)."
                )
            await db.refresh(payroll)

            try:
                from app.services.billing.auto_accounting import create_payroll_journal_entry

                payroll.employee = employee
                await create_payroll_journal_entry(db, UUID(tenant_id), payroll)
                await db.commit()
            except Exception as acc_err:
                logger.warning("Asiento de nómina no generado para %s: %s", nif, acc_err)

        payroll_numbers = {
            "base_salary": base_salary,
            "ss_contingencias_comunes": ss_cc,
            "ss_desempleo": ss_des,
            "ss_formacion_profesional": ss_fp,
            "ss_mei": ss_mei,
            "cuota_solidaridad": calc["cuota_solidaridad"],
            "irpf": irpf,
            "irpf_rate": irpf_rate,
            "other_deductions": deductions,
            "net_salary": net_salary,
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
                    db=db_ev,
                    tenant_id=UUID(tenant_id),
                    user_id=None,
                    event_name="payroll_created",
                    context={
                        "payroll_id": str(payroll.id),
                        "employee_name": employee.name,
                        "employee_nif": employee.nif,
                        "net_salary": float(net_salary),
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

        # Guard masivo: pre-cargar IDs de empleados que YA tienen nómina para
        # este period_start. Skipear esos. Sin esto cada invocación duplicaba
        # las nóminas (vimos 120 filas para el mismo set de 5 empleados).
        async with AsyncSessionLocal() as db:
            existing_result = await db.execute(
                select(Payroll.employee_id).where(
                    Payroll.tenant_id == UUID(tenant_id),
                    Payroll.period_start == start_date,
                )
            )
            existing_employee_ids = {row[0] for row in existing_result.all()}

        summary_lines = []
        skipped_lines = []
        created_count = 0
        async with AsyncSessionLocal() as db:
            for emp in employees:
                if emp.id in existing_employee_ids:
                    skipped_lines.append(
                        f"- {emp.name}: ya tenía nómina para {month:02d}/{year}, no se crea duplicado"
                    )
                    continue

                base_salary = float(emp.base_salary) if emp.base_salary else 0
                irpf_rate = float(emp.irpf_rate) if emp.irpf_rate is not None else 15.0

                calc = calc_payroll(base_salary, irpf_rate, year=year)
                ss_cc = calc["ss_contingencias_comunes"]
                ss_des = calc["ss_desempleo"]
                ss_fp = calc["ss_formacion_profesional"]
                ss_mei = calc["ss_mei"]
                irpf = calc["irpf"]
                total_ded = calc["deductions"]
                net_salary = max(0.0, calc["net_salary"])

                db.add(
                    Payroll(
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
                        cuota_solidaridad=calc["cuota_solidaridad"],
                        irpf=irpf,
                        other_deductions=0,
                        deductions=total_ded,
                        net_salary=net_salary,
                        status="draft",
                    )
                )

                payroll_numbers = {
                    "base_salary": base_salary,
                    "ss_contingencias_comunes": ss_cc,
                    "ss_desempleo": ss_des,
                    "ss_formacion_profesional": ss_fp,
                    "ss_mei": ss_mei,
                    "cuota_solidaridad": calc["cuota_solidaridad"],
                    "irpf": irpf,
                    "irpf_rate": irpf_rate,
                    "other_deductions": 0.0,
                    "net_salary": net_salary,
                }
                _, pdf_err = await _generate_and_save_payroll_pdf(
                    tenant_id, emp, payroll_numbers, start_date, end_date, month, year
                )
                if pdf_err:
                    logger.warning("Error PDF nómina masiva para %s: %s", emp.name, pdf_err)

                summary_lines.append(
                    f"- {emp.name}: Bruto {base_salary:.2f}€ → Neto {net_salary:.2f}€"
                )
                created_count += 1

            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                return (
                    "Error: una o varias nóminas ya existían (detectado por "
                    "restricción de unicidad de BD). Reintenta — esta llamada "
                    "ya no se aplicará por el guard previo."
                )

        try:
            from app.services.event_bus import emit_event

            async with AsyncSessionLocal() as db_ev:
                await emit_event(
                    db=db_ev,
                    tenant_id=UUID(tenant_id),
                    user_id=None,
                    event_name="payrolls_bulk_created",
                    context={"count": len(employees), "month": month, "year": year},
                )
        except Exception as e:
            logger.warning(
                "Error al emitir evento payrolls_bulk_created para tenant %s: %s", tenant_id, e
            )

        if created_count == 0:
            return (
                f"No se crearon nuevas nóminas para {month:02d}/{year}: "
                f"todos los empleados ({len(employees)}) ya tenían nómina para ese período.\n"
                + "\n".join(skipped_lines)
            )

        parts = [
            f"Nóminas de {month:02d}/{year} generadas en modo DRAFT: "
            f"{created_count} creadas, {len(skipped_lines)} omitidas (ya existían).",
            "",
        ]
        if summary_lines:
            parts.append("Creadas:")
            parts.extend(summary_lines)
        if skipped_lines:
            parts.append("")
            parts.append("Omitidas (no duplicar):")
            parts.extend(skipped_lines)
        parts.append("")
        parts.append(
            "IMPORTANTE: Las nóminas están en estado BORRADOR. "
            "El responsable debe revisarlas y aprobarlas desde RRHH > Nóminas."
        )
        return "\n".join(parts)
    except Exception as e:
        return f"Error al generar nóminas en bloque: {str(e)}"
