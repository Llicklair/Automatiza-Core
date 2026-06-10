"""Special HR document generators — finiquito, liquidacion, registro de jornada."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Employee, Tenant
from app.services.pdf import (
    generate_finiquito_pdf as _pdf_finiquito,
)
from app.services.pdf import (
    generate_liquidacion_finiquito_pdf as _pdf_liquidacion,
)
from app.services.pdf import (
    generate_registro_jornada_pdf as _pdf_registro_jornada,
)


async def load_employee_and_tenant(
    employee_id: UUID,
    tenant_id,
    db: AsyncSession,
) -> tuple[Employee, Tenant | None]:
    """Carga empleado y tenant. Lanza ValueError si no existe."""
    emp = await db.get(Employee, employee_id)
    if not emp or emp.tenant_id != tenant_id:
        raise ValueError("Empleado no encontrado")
    tenant = await db.get(Tenant, tenant_id)
    return emp, tenant


def generate_finiquito_pdf(
    emp: Employee, tenant: Tenant | None, payload
) -> tuple[bytes, str, dict | None]:
    """Genera el PDF de finiquito.

    Si el payload no trae conceptos, los calcula desde la ficha del empleado
    (vacaciones pendientes + prorrata de extras + indemnización por causa).
    Devuelve ``(pdf_bytes, filename, calc)`` — ``calc`` solo en modo auto,
    para que la ruta pueda persistir el Settlement.
    """
    conceptos = [c.model_dump() for c in payload.conceptos]
    total_percepciones = payload.total_percepciones
    total_deducciones = payload.total_deducciones
    liquido = payload.liquido
    calc = None

    if not conceptos:
        from app.services.hr.finiquito import calc_finiquito_for_employee

        calc = calc_finiquito_for_employee(
            emp,
            fecha_baja=payload.fecha_baja,
            causa=payload.causa_baja,
            vacaciones_pendientes_dias=float(
                getattr(payload, "vacaciones_pendientes_dias", 0) or 0
            ),
        )
        conceptos = calc["conceptos"]
        total_percepciones = calc["total_percepciones"]
        total_deducciones = calc["total_deducciones"]
        liquido = calc["total_liquido"]

    finiquito_data = {
        "employee": {"name": emp.name, "nif": emp.nif or ""},
        "company": {
            "name": tenant.name if tenant else "",
            "nif": tenant.nif if tenant else "",
            "address": tenant.address if tenant else "",
        },
        "fecha_baja": payload.fecha_baja,
        "causa_baja": payload.causa_baja,
        "conceptos": conceptos,
        "total_percepciones": total_percepciones,
        "total_deducciones": total_deducciones,
        "liquido": liquido,
        "fecha": datetime.now(UTC).isoformat(),
    }
    pdf_bytes = _pdf_finiquito(finiquito_data)
    filename = f"Finiquito_{emp.name.replace(' ', '_')}_{payload.fecha_baja[:10]}.pdf"
    return pdf_bytes, filename, calc


def generate_liquidacion_pdf(emp: Employee, tenant: Tenant | None, payload) -> tuple[bytes, str]:
    liquidacion_data = {
        "employee": {
            "name": emp.name,
            "nif": emp.nif or "",
            "naf": getattr(emp, "numero_afiliacion_ss", "") or "",
            "fecha_alta": emp.join_date.isoformat() if emp.join_date else "",
            "categoria": getattr(emp, "categoria_profesional", "") or "",
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
    pdf_bytes = _pdf_liquidacion(liquidacion_data)
    filename = f"Liquidacion_{emp.name.replace(' ', '_')}_{payload.fecha_baja[:10]}.pdf"
    return pdf_bytes, filename


def generate_registro_jornada(emp: Employee, tenant: Tenant | None, payload) -> tuple[bytes, str]:
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
    pdf_bytes = _pdf_registro_jornada(registro_data)
    mes_str = f"{payload.anio}-{payload.mes:02d}"
    filename = f"Registro_Jornada_{emp.name.replace(' ', '_')}_{mes_str}.pdf"
    return pdf_bytes, filename
