"""HR agent — employee management tools."""

import logging
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.base import AsyncSessionLocal
from app.db.models.models import Employee

logger = logging.getLogger(__name__)


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
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Employee).where(Employee.tenant_id == UUID(tenant_id)))
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
    return await _create_employee_async(
        tenant_id, name, nif, base_salary, role, department, email, irpf_rate
    )


async def _create_employee_async(
    tenant_id: str,
    name: str,
    nif: str,
    base_salary: float,
    role: str,
    department: str,
    email: str,
    irpf_rate: float,
) -> str:
    if not name.strip():
        return "Error: El nombre del empleado es obligatorio."
    if not nif.strip():
        return "Error: El NIF/DNI del empleado es obligatorio."

    try:
        normalized_nif = nif.strip().upper()
        async with AsyncSessionLocal() as db:
            # Validación case-insensitive: el insert sube a uppercase, así que
            # el query también debe ignorar case para evitar que "12345678z" y
            # "12345678Z" se traten como NIFs distintos. La BD tiene un partial
            # UNIQUE INDEX (tenant_id, UPPER(nif)) como segunda barrera.
            result = await db.execute(
                select(Employee).where(
                    Employee.tenant_id == UUID(tenant_id),
                    func.upper(Employee.nif) == normalized_nif,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return f"Error: Ya existe un empleado con NIF {nif}: {existing.name} (ID: {existing.id})."

            emp = Employee(
                tenant_id=UUID(tenant_id),
                name=name.strip(),
                nif=normalized_nif,
                email=email.strip() or None,
                base_salary=base_salary,
                role=role or None,
                department=department or None,
                irpf_rate=irpf_rate,
            )
            db.add(emp)
            try:
                await db.commit()
            except IntegrityError:
                # Race condition o validación previa fallida: el UNIQUE INDEX
                # de BD nos protege. Mensaje claro al LLM.
                await db.rollback()
                return (
                    f"Error: Ya existe un empleado con NIF {nif} en el sistema "
                    f"(detectado por restricción de unicidad de BD)."
                )
            await db.refresh(emp)

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
