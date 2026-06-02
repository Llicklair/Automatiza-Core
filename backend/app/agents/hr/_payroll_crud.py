"""HR agent — payroll CRUD tools (update, approve, list)."""

import logging
from calendar import monthrange
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select

from app.agents.shared.validators.billing import APPROVAL_THRESHOLD_EUR
from app.db.base import AsyncSessionLocal
from app.db.models.models import Employee, Payroll

logger = logging.getLogger(__name__)


@tool
async def update_payroll(
    tenant_id: str,
    payroll_id: str,
    base_salary: str = "",
    deductions: str = "",
    notes: str = "",
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
    tenant_id: str,
    payroll_id: str,
    base_salary_str: str,
    deductions_str: str,
    notes: str,
) -> str:
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

            base = float(payroll.base_salary)
            if base_salary_str.strip():
                try:
                    base = float(base_salary_str.strip().replace(",", "."))
                    payroll.base_salary = base
                    changes.append(f"bruto={base:.2f}€")
                except ValueError:
                    return f"Error: Salario base no válido: '{base_salary_str}'."

            extra_ded = float(payroll.other_deductions or 0)
            if deductions_str.strip():
                try:
                    extra_ded = float(deductions_str.strip().replace(",", "."))
                    payroll.other_deductions = extra_ded
                    changes.append(f"deducciones_extra={extra_ded:.2f}€")
                except ValueError:
                    return f"Error: Deducciones no válidas: '{deductions_str}'."

            # Cast explícito a float en ambos lados: payroll.base_salary recién
            # se asignó como float pero payroll.irpf sigue siendo Decimal (no
            # se ha tocado todavía). Decimal / float lanza TypeError.
            irpf_rate = (
                float(payroll.irpf) / float(payroll.base_salary) * 100
                if payroll.base_salary and float(payroll.base_salary) > 0
                else 15.0
            )
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
async def approve_payroll(
    tenant_id: str, payroll_id: str = "", approve_all: bool = False, month: int = 0, year: int = 0
) -> str:
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
    tenant_id: str,
    payroll_id: str,
    approve_all: bool,
    month: int,
    year: int,
) -> str:
    from sqlalchemy import and_

    try:
        async with AsyncSessionLocal() as db:
            if approve_all:
                if not month or not year:
                    return "Error: Para aprobar todas las nóminas, indica mes y año."
                start_date = datetime(year, month, 1, tzinfo=UTC)
                last_day = monthrange(year, month)[1]
                end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)

                result = await db.execute(
                    select(Payroll).where(
                        and_(
                            Payroll.tenant_id == UUID(tenant_id),
                            Payroll.status == "draft",
                            Payroll.period_start >= start_date,
                            Payroll.period_end <= end_date,
                        )
                    )
                )
                payrolls = result.scalars().all()
                if not payrolls:
                    return f"No hay nóminas en borrador para {month}/{year}."

                total_net = sum((Decimal(str(p.net_salary or 0)) for p in payrolls), Decimal(0))
                if total_net > APPROVAL_THRESHOLD_EUR:
                    return (
                        f"APROBACIÓN REQUERIDA: El total de {len(payrolls)} nóminas de "
                        f"{month}/{year} ({total_net:.2f}€) supera el umbral de "
                        f"{APPROVAL_THRESHOLD_EUR:.0f}€.\nLas nóminas NO se han aprobado. "
                        f"Requiere aprobación humana desde el dashboard."
                    )

                for p in payrolls:
                    p.status = "approved"
                await db.commit()

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

                if Decimal(str(payroll.net_salary or 0)) > APPROVAL_THRESHOLD_EUR:
                    return (
                        f"APROBACIÓN REQUERIDA: La nómina {payroll_id[:8]}... "
                        f"({float(payroll.net_salary):.2f}€) supera el umbral de "
                        f"{APPROVAL_THRESHOLD_EUR:.0f}€.\nNO se ha aprobado. "
                        f"Requiere aprobación humana desde el dashboard."
                    )

                payroll.status = "approved"
                await db.commit()
                return (
                    f"Nómina {payroll_id[:8]}... aprobada. Neto: {float(payroll.net_salary):.2f}€."
                )
    except Exception as e:
        return f"Error aprobando nómina: {e}"


@tool
async def list_payrolls(
    tenant_id: str, month: int = 0, year: int = 0, status_filter: str = "all"
) -> str:
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
                f"Nóminas ({len(rows)}):\n" + "\n".join(lines) + f"\n\nTotal neto: {total_net:.2f}€"
            )
    except Exception as e:
        return f"Error listando nóminas: {e}"
