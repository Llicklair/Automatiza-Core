"""HR agent — employee management tools (thin wrappers over services/hr)."""

import logging
from uuid import UUID

from langchain_core.tools import tool

from app.db.base import AsyncSessionLocal

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
    from app.services.hr.queries import list_employees as list_employees_svc

    try:
        async with AsyncSessionLocal() as db:
            employees = await list_employees_svc(UUID(tenant_id), db)

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
    tenant_id: str,
    name: str,
    nif: str,
    base_salary: float,
    role: str,
    department: str,
    email: str,
    irpf_rate: float,
) -> str:
    from app.services.hr.commands import create_employee as create_employee_svc

    if not name.strip():
        return "Error: El nombre del empleado es obligatorio."
    if not nif.strip():
        return "Error: El NIF/DNI del empleado es obligatorio."

    try:
        async with AsyncSessionLocal() as db:
            emp = await create_employee_svc(
                {
                    "name": name.strip(),
                    "nif": nif,
                    "email": email.strip() or None,
                    "base_salary": base_salary,
                    "role": role or None,
                    "department": department or None,
                    "irpf_rate": irpf_rate,
                },
                UUID(tenant_id),
                db,
            )
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
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error creando empleado: {e}"
