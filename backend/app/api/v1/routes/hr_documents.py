"""Asesoría Documental — Generación de documentos laborales con IA.

Endpoints:
  POST /hr/documents/generate  — Genera un borrador con LLM
  GET  /hr/documents           — Lista documentos generados del tenant
  GET  /hr/documents/{id}      — Detalle de un documento
  POST /hr/documents/{id}/approve — Marca como aprobado
  DELETE /hr/documents/{id}    — Elimina un borrador
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, Column, DateTime, String, Text, desc, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import Base, get_db
from app.db.models.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hr/documents", tags=["hr-documents"])


# ── Modelo DB ──────────────────────────────────────────────────────────────────


class HRDocument(Base):
    """Documento laboral generado por IA. Append-mostly: se crea como borrador
    y se aprueba una vez. Nunca se edita el contenido — se regenera."""

    __tablename__ = "hr_documents"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), index=True, nullable=False)
    doc_type = Column(
        String(50), nullable=False
    )  # contract, nda, termination, settlement, addendum, other
    title = Column(String(255), nullable=False)
    employee_name = Column(String(200), nullable=True)  # Optional employee target
    content_html = Column(Text, nullable=False)  # HTML rendered by LLM
    status = Column(String(20), default="draft")  # draft | approved
    instructions = Column(Text, nullable=True)  # User's original prompt
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    approved_at = Column(DateTime, nullable=True)


# ── Schemas ────────────────────────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    doc_type: str  # contract, nda, termination, settlement, addendum, other
    instructions: str = ""  # Free-text description of what to generate
    employee_name: str | None = None  # Optional: auto-fill employee data
    employee_id: str | None = None  # Optional: pull data from HR module


class HRDocumentOut(BaseModel):
    id: str
    doc_type: str
    title: str
    employee_name: str | None
    content_html: str
    status: str
    instructions: str | None
    created_at: str
    approved_at: str | None

    model_config = ConfigDict(from_attributes=True)


# ── Logo oficial SEPE (cargado una vez al arrancar) ────────────────────────────

import base64 as _b64
import os as _os


def _load_sepe_logo_b64() -> str:
    """Carga el logo SEPE como data URI PNG para embeber en HTML."""
    candidates = [
        _os.path.join(
            _os.path.dirname(__file__), "..", "..", "services", "assets", "sepe_logo.png"
        ),
        _os.path.join(_os.path.dirname(__file__), "assets", "sepe_logo.png"),
    ]
    for path in candidates:
        p = _os.path.normpath(path)
        if _os.path.isfile(p):
            with open(p, "rb") as f:
                return "data:image/png;base64," + _b64.b64encode(f.read()).decode()
    return ""  # fallback: sin logo


_SEPE_LOGO_URI = _load_sepe_logo_b64()

# ── Cabecera HTML oficial SEPE (para contratos de trabajo) ─────────────────────

_HEADER_SEPE = f"""
<table style="width:100%;border:none;margin-bottom:6px">
  <tr>
    <td style="border:none;padding:0;vertical-align:top;width:60%">
      <div style="font-family:Arial,sans-serif;font-size:7.5pt;color:#555;line-height:1.5">
        <strong style="font-size:8pt;color:#222">GOBIERNO DE ESPAÑA</strong><br>
        MINISTERIO DE TRABAJO Y ECONOMÍA SOCIAL<br>
        SERVICIO PÚBLICO DE EMPLEO ESTATAL
      </div>
    </td>
    <td style="border:none;padding:0;text-align:right;vertical-align:top">
      {'<img src="' + _SEPE_LOGO_URI + '" style="height:38px" alt="SEPE"/>' if _SEPE_LOGO_URI else '<span style="font-size:16pt;font-weight:bold;color:#005495">SEPE</span>'}
    </td>
  </tr>
</table>
<hr style="border:none;border-top:2px solid #005495;margin:4px 0 14px">
"""

# ── Cabecera HTML para documentos de empresa (nóminas, finiquitos, NDA) ────────

_HEADER_EMPRESA = """
<div style="font-family:Arial,sans-serif;font-size:9pt;color:#333;margin-bottom:16px">
  <strong style="font-size:12pt;color:#1a1a1a">[EMPRESA_NOMBRE]</strong><br>
  NIF: [NIF_EMPRESA] &nbsp;|&nbsp; [DIRECCIÓN_EMPRESA]<br>
  <span style="font-size:8pt;color:#666">Tel.: [TEL_EMPRESA] &nbsp;·&nbsp; [EMAIL_EMPRESA]</span>
</div>
<hr style="border:none;border-top:1px solid #ccc;margin:4px 0 14px">
"""

# ── System Prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT_BASE = """Eres un asesor jurídico-laboral especializado en documentación de empresas españolas.
Tu ÚNICA función es escribir el HTML del documento directamente en tu respuesta.

REGLAS ESTRICTAS:
1. IMPORTANTE: Responde ÚNICAMENTE con HTML puro. Sin markdown, sin bloques de código, sin explicaciones.
2. Sustituye TODOS los datos reales de empresa y empleado que se te proporcionan. NUNCA dejes un dato real como placeholder si lo tienes.
3. Si falta algún dato, usa marcadores claros: [NIF_EMPRESA], [DIRECCIÓN_EMPRESA], [GRUPO_PROFESIONAL], etc.
4. NO incluyas banners rojos ni avisos de "BORRADOR". Solo una nota discreta al final: "Borrador — revisar antes de firmar."
5. La ley aplicable es la legislación española vigente: ET R.D.L. 2/2015, RD 2064/1995 (nóminas), ET reforma 2021.
6. SIEMPRE incluye al final un bloque de firmas (empresa + trabajador + representante legal si procede).

ESTILOS BASE (aplica siempre a body):
  font-family: Arial, sans-serif; font-size: 11pt; color: #1a1a1a; background: #fff;
  max-width: 800px; margin: 0 auto; padding: 40px; line-height: 1.6

ESTILOS DE ELEMENTOS:
  h1: font-size:13pt; text-align:center; text-transform:uppercase; letter-spacing:1px; border-bottom:2px solid #1a1a1a; padding-bottom:6px; margin-top:10px
  h2: font-size:11pt; text-transform:uppercase; color:#333; border-bottom:1px solid #ccc; padding-bottom:3px; margin-top:20px
  table: width:100%; border-collapse:collapse; margin:8px 0; font-size:10.5pt
  td,th: padding:5px 10px; border:1px solid #ccc
  th: background:#f5f5f5; font-weight:bold; text-align:left
  .firma-bloque: display:inline-block; width:44%; text-align:center; margin-top:50px; vertical-align:top
  .firma-linea: border-top:1px solid #333; margin-top:60px; padding-top:6px; font-size:10pt
  .nota-final: font-size:8.5pt; color:#999; text-align:center; margin-top:40px; border-top:1px solid #eee; padding-top:10px
"""


def _get_system_prompt(doc_type: str) -> str:
    """Devuelve el system prompt adaptado al tipo de documento."""
    if doc_type == "contract":
        header_instruction = f"""
CABECERA OBLIGATORIA para contratos de trabajo — copia este HTML exactamente al inicio del documento:
{_HEADER_SEPE}

ESTRUCTURA DEL CONTRATO (sigue este orden):
1. Cabecera SEPE (arriba)
2. Título: "CONTRATO DE TRABAJO" (h1)
3. Subtítulo con modalidad (ej: "INDEFINIDO ORDINARIO — Código 100")
4. Tabla: DATOS DE LA EMPRESA (razón social, CIF, CNAE, CCC, domicilio, representante)
5. Tabla: DATOS DEL TRABAJADOR (nombre, DNI/NIE, NAF, fecha nacimiento, domicilio, grupo cotización)
6. Sección: DURACIÓN DE LA RELACIÓN LABORAL (fecha inicio, fin si temporal, período de prueba)
7. Sección: JORNADA DE TRABAJO (completa/parcial, horas/semana, horario, distribución)
8. Sección: RETRIBUCIÓN (salario base, complementos, pagas extra, total anual bruto)
9. Sección: CONVENIO COLECTIVO APLICABLE
10. Sección: CLÁUSULAS ADICIONALES
11. Bloque de firmas (empresa + trabajador + fecha y lugar)
12. Nota discreta al final
"""
    elif doc_type == "settlement":
        header_instruction = """
ESTRUCTURA DEL FINIQUITO (sigue este orden):
1. Cabecera empresa (nombre, NIF, dirección)
2. Título: "FINIQUITO / DOCUMENTO DE LIQUIDACIÓN Y SALDO" (h1)
3. Datos empresa y trabajador en tabla
4. Párrafo de declaración de extinción (causa, fecha)
5. Tabla DESGLOSE DE LA LIQUIDACIÓN con columnas CONCEPTOS | DÍAS/BASE | DEVENGOS | DEDUCCIONES:
   - Parte proporcional de vacaciones no disfrutadas
   - Parte proporcional paga extra (si aplica)
   - Parte proporcional aguinaldo (si aplica)
   - MEI (si aplica)
   - Indemnización (si aplica — indicar días/año y base)
   - IRPF (%)
   - Cotización SS obrero
6. TOTAL PERCEPCIONES | TOTAL DEDUCCIONES | IMPORTE LÍQUIDO A PERCIBIR
7. Párrafo legal de saldo y finiquito (el trabajador declara no tener más reclamaciones)
8. Espacio para 3 firmas: empresa, trabajador, representante sindical (si aplica)
9. Lugar, fecha y nota discreta
"""
    elif doc_type == "termination":
        header_instruction = """
ESTRUCTURA CARTA DE DESPIDO:
1. Cabecera empresa
2. Lugar y fecha
3. Datos destinatario (trabajador)
4. Cuerpo: causa de despido con fundamento legal (ET art. 52/54 según sea objetivo/disciplinario)
5. Efectos: fecha de efectividad, indemnización si procede
6. Firma empresa
"""
    else:
        header_instruction = """
Usa un encabezado profesional con datos de empresa, título del documento y datos de las partes.
"""

    return _SYSTEM_PROMPT_BASE + header_instruction


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_hr_document(
    payload: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera un borrador de documento laboral usando el LLM."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.core.llm_factory import get_llm_for_tenant

    # Build context with employee data if provided
    employee_context = ""
    if payload.employee_id:
        try:
            from app.db.models.hr import Employee

            result = await db.execute(
                select(Employee).where(
                    Employee.id == payload.employee_id,
                    Employee.tenant_id == current_user.tenant_id,
                )
            )
            emp = result.scalar_one_or_none()
            if emp:
                employee_context = (
                    f"\nDATOS DEL TRABAJADOR (usa estos exactamente):\n"
                    f"- Nombre completo: {emp.name}\n"
                    f"- DNI/NIE: {emp.nif or '[DNI_EMPLEADO]'}\n"
                    f"- NAF (Núm. Afiliación SS): {getattr(emp, 'numero_afiliacion_ss', None) or '[NAF]'}\n"
                    f"- Categoría profesional: {getattr(emp, 'categoria_profesional', None) or emp.role or '[CATEGORÍA]'}\n"
                    f"- Grupo de cotización: {getattr(emp, 'grupo_cotizacion', None) or '[GRUPO_COT]'}\n"
                    f"- Departamento: {emp.department or '[DEPARTAMENTO]'}\n"
                    f"- Tipo de contrato: {getattr(emp, 'tipo_contrato', None) or '[TIPO_CONTRATO]'}\n"
                    f"- Jornada: {getattr(emp, 'jornada_tipo', 'completa')} — {getattr(emp, 'jornada_horas_semana', None) or 40}h/semana\n"
                    f"- Convenio colectivo: {getattr(emp, 'convenio_colectivo', None) or '[CONVENIO]'}\n"
                    f"- Salario base mensual: {emp.base_salary or '[SALARIO]'}€\n"
                    f"- IRPF: {emp.irpf_rate or 15}%\n"
                    f"- Fecha incorporación: {emp.join_date or '[FECHA_INICIO]'}\n"
                    f"- Período de prueba: {getattr(emp, 'periodo_prueba_dias', None) or '[PERIODO_PRUEBA]'} días\n"
                )
        except Exception as e:
            logger.warning("No se pudo cargar empleado %s: %s", payload.employee_id, e)

    # Tenant data for company header
    try:
        from app.db.models.auth import Tenant

        result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
        tenant = result.scalar_one_or_none()
        company_context = ""
        if tenant:
            company_context = (
                f"\nDATOS REALES DE LA EMPRESA (usa estos exactamente, no los sustituyas por placeholders):\n"
                f"- Razón social: {tenant.name}\n"
                f"- CIF/NIF: {tenant.nif or '[CIF_EMPRESA]'}\n"
                f"- Dirección: {tenant.address or '[DIRECCIÓN_EMPRESA]'}\n"
                f"- Teléfono: {tenant.phone or '[TEL_EMPRESA]'}\n"
                f"- Email de contacto: {tenant.contact_email or '[EMAIL_EMPRESA]'}\n"
            )
    except Exception as e:
        logger.warning("No se pudo cargar datos del tenant: %s", e)
        company_context = ""

    doc_type_labels = {
        "contract": "Contrato de Trabajo",
        "nda": "Acuerdo de Confidencialidad (NDA)",
        "termination": "Carta de Despido",
        "settlement": "Finiquito",
        "addendum": "Adenda Contractual",
        "other": "Documento Laboral",
    }
    title = doc_type_labels.get(payload.doc_type, "Documento Laboral")
    if payload.employee_name:
        title += f" — {payload.employee_name}"

    user_prompt = (
        f"Genera un documento de tipo: {payload.doc_type} ({title})\n"
        f"Instrucciones del usuario: {payload.instructions}\n"
        f"{company_context}{employee_context}\n"
        f"Nombre del empleado destinatario: {payload.employee_name or '[NOMBRE_EMPLEADO]'}"
    )

    try:
        llm = await get_llm_for_tenant(current_user.tenant_id, db, temperature=0.3)
    except Exception as e:
        logger.error("Error obteniendo LLM: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al inicializar el modelo IA: {str(e)}")

    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=_get_system_prompt(payload.doc_type)),
                HumanMessage(content=user_prompt),
            ]
        )
        content_html = response.content.strip()
        # Eliminar wrappers de markdown (```html ... ```)
        if content_html.startswith("```"):
            lines = content_html.split("\n")
            start = 1 if lines[0].startswith("```") else 0
            end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
            content_html = "\n".join(lines[start:end]).strip()
    except Exception as e:
        logger.error("Error generando documento con LLM: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al generar el documento: {str(e)}")

    # Usar sesión fresca para el save — la sesión anterior puede haber expirado
    try:
        from app.db.base import AsyncSessionLocal

        async with AsyncSessionLocal() as save_db:
            doc = HRDocument(
                id=uuid.uuid4(),
                tenant_id=current_user.tenant_id,
                doc_type=payload.doc_type,
                title=title,
                employee_name=payload.employee_name,
                content_html=content_html,
                instructions=payload.instructions,
                status="draft",
            )
            save_db.add(doc)
            await save_db.commit()
            await save_db.refresh(doc)
    except Exception as e:
        logger.error("Error guardando documento en BD: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Documento generado pero no guardado: {str(e)}"
        )

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


@router.get("", response_model=list[HRDocumentOut])
async def list_hr_documents(
    doc_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista documentos generados del tenant, filtrados opcionalmente."""
    query = (
        select(HRDocument)
        .where(HRDocument.tenant_id == current_user.tenant_id)
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
        HRDocumentOut(
            id=str(d.id),
            doc_type=d.doc_type,
            title=d.title,
            employee_name=d.employee_name,
            content_html=d.content_html,
            status=d.status,
            instructions=d.instructions,
            created_at=d.created_at.isoformat(),
            approved_at=d.approved_at.isoformat() if d.approved_at else None,
        )
        for d in docs
    ]


@router.get("/{doc_id}")
async def get_hr_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(HRDocument).where(
            HRDocument.id == doc_id,
            HRDocument.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
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


@router.post("/{doc_id}/approve")
async def approve_hr_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(HRDocument).where(
            HRDocument.id == doc_id,
            HRDocument.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    doc.status = "approved"
    doc.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(doc.id), "status": "approved", "approved_at": doc.approved_at.isoformat()}


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hr_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(HRDocument).where(
            HRDocument.id == doc_id,
            HRDocument.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    await db.delete(doc)
    await db.commit()
