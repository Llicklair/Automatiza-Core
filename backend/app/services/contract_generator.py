"""Rellena plantillas .docx con variables de BD usando docxtpl.

Uso:
    context = build_context_for_client(client, tenant)
    docx_bytes = generate_contract(template_path, context)
"""
import io
import uuid
from datetime import date


def _fmt_date(dt) -> str:
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y")


def _tenant_context(tenant) -> dict:
    return {
        "nombre_empresa": tenant.name or "",
        "nif_empresa": tenant.nif or "",
        "direccion_empresa": tenant.address or "",
        "email_empresa": tenant.contact_email or "",
        "telefono_empresa": tenant.phone or "",
    }


def build_context_for_client(client, tenant) -> dict:
    today = date.today()
    ctx = {
        "nombre_cliente": client.name or "",
        "nif_cliente": client.nif or "",
        "direccion_cliente": client.address or "",
        "email_cliente": client.email or "",
        "telefono_cliente": client.phone or "",
        "fecha": today.strftime("%d/%m/%Y"),
        "numero_contrato": f"CT-{today.year}-{uuid.uuid4().hex[:6].upper()}",
    }
    ctx.update(_tenant_context(tenant))
    return ctx


def build_context_for_employee(employee, tenant) -> dict:
    today = date.today()
    ctx = {
        "nombre_empleado": employee.name or "",
        "nif_empleado": employee.nif or "",
        "email_empleado": employee.email or "",
        "departamento": employee.department or "",
        "puesto": employee.role or "",
        "salario_base": str(employee.base_salary or ""),
        "fecha_inicio": _fmt_date(employee.join_date),
        "fecha_fin_contrato": _fmt_date(employee.contract_end_date),
        # Aliases que también puede usar la plantilla
        "nombre_cliente": employee.name or "",
        "nif_cliente": employee.nif or "",
        "fecha": today.strftime("%d/%m/%Y"),
        "numero_contrato": f"CT-{today.year}-{uuid.uuid4().hex[:6].upper()}",
    }
    ctx.update(_tenant_context(tenant))
    return ctx


def generate_contract(template_path: str, context: dict) -> bytes:
    """Rellena el .docx y devuelve los bytes resultantes.

    Raises:
        ImportError: si docxtpl no está instalado.
        Exception: cualquier error de docxtpl (plantilla inválida, variable mal formada…).
    """
    from docxtpl import DocxTemplate  # lazy import — no falla si no está en dev

    tpl = DocxTemplate(template_path)
    tpl.render(context)
    buf = io.BytesIO()
    tpl.save(buf)
    return buf.getvalue()
