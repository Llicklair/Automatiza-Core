"""Business logic for HR Document generation and management."""

import base64
import logging
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.prompts import load_prompt

logger = logging.getLogger(__name__)

# ── SEPE logo (loaded once at import time) ────────────────────────────────────


def _load_sepe_logo_b64() -> str:
    """Load SEPE logo as a data URI PNG for embedding in HTML."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "assets", "sepe_logo.png"),
        os.path.join(
            os.path.dirname(__file__), "..", "api", "v1", "routes", "assets", "sepe_logo.png"
        ),
    ]
    for path in candidates:
        p = os.path.normpath(path)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    return ""


_SEPE_LOGO_URI = _load_sepe_logo_b64()

_HEADER_SEPE = f"""
<table style="width:100%;border:none;margin-bottom:6px">
  <tr>
    <td style="border:none;padding:0;vertical-align:top;width:60%">
      <div style="font-family:Arial,sans-serif;font-size:7.5pt;color:#555;line-height:1.5">
        <strong style="font-size:8pt;color:#222">GOBIERNO DE ESPANA</strong><br>
        MINISTERIO DE TRABAJO Y ECONOMIA SOCIAL<br>
        SERVICIO PUBLICO DE EMPLEO ESTATAL
      </div>
    </td>
    <td style="border:none;padding:0;text-align:right;vertical-align:top">
      {'<img src="' + _SEPE_LOGO_URI + '" style="height:38px" alt="SEPE"/>' if _SEPE_LOGO_URI else '<span style="font-size:16pt;font-weight:bold;color:#005495">SEPE</span>'}
    </td>
  </tr>
</table>
<hr style="border:none;border-top:2px solid #005495;margin:4px 0 14px">
"""

_HEADER_EMPRESA = """
<div style="font-family:Arial,sans-serif;font-size:9pt;color:#333;margin-bottom:16px">
  <strong style="font-size:12pt;color:#1a1a1a">[EMPRESA_NOMBRE]</strong><br>
  NIF: [NIF_EMPRESA] &nbsp;|&nbsp; [DIRECCION_EMPRESA]<br>
  <span style="font-size:8pt;color:#666">Tel.: [TEL_EMPRESA] &nbsp;·&nbsp; [EMAIL_EMPRESA]</span>
</div>
<hr style="border:none;border-top:1px solid #ccc;margin:4px 0 14px">
"""

DOC_TYPE_LABELS = {
    "contract": "Contrato de Trabajo",
    "nda": "Acuerdo de Confidencialidad (NDA)",
    "termination": "Carta de Despido",
    "settlement": "Finiquito",
    "addendum": "Adenda Contractual",
    "other": "Documento Laboral",
}

# ── Header instructions per doc type ─────────────────────────────────────────

_HEADER_INSTRUCTIONS: dict[str, str] = {
    "contract": f"""
CABECERA OBLIGATORIA para contratos de trabajo — copia este HTML exactamente al inicio del documento:
{_HEADER_SEPE}

ESTRUCTURA DEL CONTRATO (sigue este orden):
1. Cabecera SEPE (arriba)
2. Titulo: "CONTRATO DE TRABAJO" (h1)
3. Subtitulo con modalidad (ej: "INDEFINIDO ORDINARIO — Codigo 100")
4. Tabla: DATOS DE LA EMPRESA (razon social, CIF, CNAE, CCC, domicilio, representante)
5. Tabla: DATOS DEL TRABAJADOR (nombre, DNI/NIE, NAF, fecha nacimiento, domicilio, grupo cotizacion)
6. Seccion: DURACION DE LA RELACION LABORAL (fecha inicio, fin si temporal, periodo de prueba)
7. Seccion: JORNADA DE TRABAJO (completa/parcial, horas/semana, horario, distribucion)
8. Seccion: RETRIBUCION (salario base, complementos, pagas extra, total anual bruto)
9. Seccion: CONVENIO COLECTIVO APLICABLE
10. Seccion: CLAUSULAS ADICIONALES
11. Bloque de firmas (empresa + trabajador + fecha y lugar)
12. Nota discreta al final
""",
    "settlement": """
ESTRUCTURA DEL FINIQUITO (sigue este orden):
1. Cabecera empresa (nombre, NIF, direccion)
2. Titulo: "FINIQUITO / DOCUMENTO DE LIQUIDACION Y SALDO" (h1)
3. Datos empresa y trabajador en tabla
4. Parrafo de declaracion de extincion (causa, fecha)
5. Tabla DESGLOSE DE LA LIQUIDACION con columnas CONCEPTOS | DIAS/BASE | DEVENGOS | DEDUCCIONES:
   - Parte proporcional de vacaciones no disfrutadas
   - Parte proporcional paga extra (si aplica)
   - Parte proporcional aguinaldo (si aplica)
   - MEI (si aplica)
   - Indemnizacion (si aplica — indicar dias/ano y base)
   - IRPF (%)
   - Cotizacion SS obrero
6. TOTAL PERCEPCIONES | TOTAL DEDUCCIONES | IMPORTE LIQUIDO A PERCIBIR
7. Parrafo legal de saldo y finiquito (el trabajador declara no tener mas reclamaciones)
8. Espacio para 3 firmas: empresa, trabajador, representante sindical (si aplica)
9. Lugar, fecha y nota discreta
""",
    "termination": """
ESTRUCTURA CARTA DE DESPIDO:
1. Cabecera empresa
2. Lugar y fecha
3. Datos destinatario (trabajador)
4. Cuerpo: causa de despido con fundamento legal (ET art. 52/54 segun sea objetivo/disciplinario)
5. Efectos: fecha de efectividad, indemnizacion si procede
6. Firma empresa
""",
}

_DEFAULT_HEADER_INSTRUCTION = """
Usa un encabezado profesional con datos de empresa, titulo del documento y datos de las partes.
"""


def _get_system_prompt(doc_type: str) -> str:
    """Build system prompt for the given document type."""
    base = load_prompt("hr_documents")
    header = _HEADER_INSTRUCTIONS.get(doc_type, _DEFAULT_HEADER_INSTRUCTION)
    return base + header


# ── Employee context builder ──────────────────────────────────────────────────


async def _build_employee_context(employee_id: str, tenant_id, db: AsyncSession) -> str:
    """Fetch employee data and format as LLM context string."""
    try:
        from app.db.models.hr import Employee

        result = await db.execute(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.tenant_id == tenant_id,
            )
        )
        emp = result.scalar_one_or_none()
        if not emp:
            return ""
        return (
            f"\nDATOS DEL TRABAJADOR (usa estos exactamente):\n"
            f"- Nombre completo: {emp.name}\n"
            f"- DNI/NIE: {emp.nif or '[DNI_EMPLEADO]'}\n"
            f"- NAF (Num. Afiliacion SS): {getattr(emp, 'numero_afiliacion_ss', None) or '[NAF]'}\n"
            f"- Categoria profesional: {getattr(emp, 'categoria_profesional', None) or emp.role or '[CATEGORIA]'}\n"
            f"- Grupo de cotizacion: {getattr(emp, 'grupo_cotizacion', None) or '[GRUPO_COT]'}\n"
            f"- Departamento: {emp.department or '[DEPARTAMENTO]'}\n"
            f"- Tipo de contrato: {getattr(emp, 'tipo_contrato', None) or '[TIPO_CONTRATO]'}\n"
            f"- Jornada: {getattr(emp, 'jornada_tipo', 'completa')} — {getattr(emp, 'jornada_horas_semana', None) or 40}h/semana\n"
            f"- Convenio colectivo: {getattr(emp, 'convenio_colectivo', None) or '[CONVENIO]'}\n"
            f"- Salario base mensual: {emp.base_salary or '[SALARIO]'}€\n"
            f"- IRPF: {emp.irpf_rate or 15}%\n"
            f"- Fecha incorporacion: {emp.join_date or '[FECHA_INICIO]'}\n"
            f"- Periodo de prueba: {getattr(emp, 'periodo_prueba_dias', None) or '[PERIODO_PRUEBA]'} dias\n"
        )
    except Exception as e:
        logger.warning("No se pudo cargar empleado %s: %s", employee_id, e)
        return ""


async def _build_company_context(tenant_id, db: AsyncSession) -> str:
    """Fetch tenant data and format as LLM context string."""
    try:
        from app.db.models.auth import Tenant

        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            return ""
        return (
            f"\nDATOS REALES DE LA EMPRESA (usa estos exactamente, no los sustituyas por placeholders):\n"
            f"- Razon social: {tenant.name}\n"
            f"- CIF/NIF: {tenant.nif or '[CIF_EMPRESA]'}\n"
            f"- Direccion: {tenant.address or '[DIRECCION_EMPRESA]'}\n"
            f"- Telefono: {tenant.phone or '[TEL_EMPRESA]'}\n"
            f"- Email de contacto: {tenant.contact_email or '[EMAIL_EMPRESA]'}\n"
        )
    except Exception as e:
        logger.warning("No se pudo cargar datos del tenant: %s", e)
        return ""


def _strip_markdown_wrapper(content: str) -> str:
    """Remove ```html ... ``` wrappers from LLM output."""
    if content.startswith("```"):
        lines = content.split("\n")
        start = 1 if lines[0].startswith("```") else 0
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        return "\n".join(lines[start:end]).strip()
    return content


# ── Public service functions ──────────────────────────────────────────────────


async def generate_document(
    doc_type: str,
    instructions: str,
    employee_name: str | None,
    employee_id: str | None,
    tenant_id,
    db: AsyncSession,
) -> dict:
    """Generate an HR document draft using LLM. Returns dict with doc fields.

    Raises:
        ValueError: on LLM init or generation failure, or DB save failure.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.core.llm_factory import get_llm_for_tenant

    # Build context
    employee_context = ""
    if employee_id:
        employee_context = await _build_employee_context(employee_id, tenant_id, db)

    company_context = await _build_company_context(tenant_id, db)

    title = DOC_TYPE_LABELS.get(doc_type, "Documento Laboral")
    if employee_name:
        title += f" — {employee_name}"

    user_prompt = (
        f"Genera un documento de tipo: {doc_type} ({title})\n"
        f"Instrucciones del usuario: {instructions}\n"
        f"{company_context}{employee_context}\n"
        f"Nombre del empleado destinatario: {employee_name or '[NOMBRE_EMPLEADO]'}"
    )

    try:
        llm = await get_llm_for_tenant(tenant_id, db, temperature=0.3)
    except Exception as e:
        logger.error("Error obteniendo LLM: %s", e)
        raise ValueError(f"Error al inicializar el modelo IA: {e}") from e

    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=_get_system_prompt(doc_type)),
                HumanMessage(content=user_prompt),
            ]
        )
        content_html = _strip_markdown_wrapper(response.content.strip())
    except Exception as e:
        logger.error("Error generando documento con LLM: %s", e)
        raise ValueError(f"Error al generar el documento: {e}") from e

    # Save with fresh session to avoid expiry issues
    try:
        from app.db.base import AsyncSessionLocal
        from app.db.models.hr_documents import HRDocument

        async with AsyncSessionLocal() as save_db:
            doc = HRDocument(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                doc_type=doc_type,
                title=title,
                employee_name=employee_name,
                content_html=content_html,
                instructions=instructions,
                status="draft",
            )
            save_db.add(doc)
            await save_db.commit()
            await save_db.refresh(doc)
    except Exception as e:
        logger.error("Error guardando documento en BD: %s", e)
        raise ValueError(f"Documento generado pero no guardado: {e}") from e

    return {
        "id": str(doc.id),
        "title": doc.title,
        "doc_type": doc.doc_type,
        "employee_name": doc.employee_name,
        "content_html": doc.content_html,
        "status": doc.status,
        "instructions": doc.instructions,
        "created_at": doc.created_at.isoformat(),
        "approved_at": None,
    }


async def list_documents(
    tenant_id,
    db: AsyncSession,
    *,
    doc_type: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List HR documents for a tenant with optional filters."""
    from app.db.models.hr_documents import HRDocument

    query = (
        select(HRDocument)
        .where(HRDocument.tenant_id == tenant_id)
        .order_by(desc(HRDocument.created_at))
        .limit(limit)
        .offset(offset)
    )
    if doc_type:
        query = query.where(HRDocument.doc_type == doc_type)
    if status_filter:
        query = query.where(HRDocument.status == status_filter)

    result = await db.execute(query)
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "title": d.title,
            "employee_name": d.employee_name,
            "content_html": d.content_html,
            "status": d.status,
            "instructions": d.instructions,
            "created_at": d.created_at.isoformat(),
            "approved_at": d.approved_at.isoformat() if d.approved_at else None,
        }
        for d in docs
    ]


async def get_document(doc_id: str, tenant_id, db: AsyncSession) -> dict:
    """Fetch a single HR document. Raises ValueError if not found."""
    from app.db.models.hr_documents import HRDocument

    result = await db.execute(
        select(HRDocument).where(
            HRDocument.id == doc_id,
            HRDocument.tenant_id == tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError("Documento no encontrado")
    return {
        "id": str(doc.id),
        "doc_type": doc.doc_type,
        "title": doc.title,
        "employee_name": doc.employee_name,
        "content_html": doc.content_html,
        "status": doc.status,
        "instructions": doc.instructions,
        "created_at": doc.created_at.isoformat(),
        "approved_at": doc.approved_at.isoformat() if doc.approved_at else None,
    }


async def approve_document(doc_id: str, tenant_id, db: AsyncSession) -> dict:
    """Mark a document as approved. Raises ValueError if not found."""
    from app.db.models.hr_documents import HRDocument

    result = await db.execute(
        select(HRDocument).where(
            HRDocument.id == doc_id,
            HRDocument.tenant_id == tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError("Documento no encontrado")

    doc.status = "approved"
    doc.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(doc.id), "status": "approved", "approved_at": doc.approved_at.isoformat()}


async def delete_document(doc_id: str, tenant_id, db: AsyncSession) -> None:
    """Delete a document. Raises ValueError if not found."""
    from app.db.models.hr_documents import HRDocument

    result = await db.execute(
        select(HRDocument).where(
            HRDocument.id == doc_id,
            HRDocument.tenant_id == tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError("Documento no encontrado")
    await db.delete(doc)
    await db.commit()
