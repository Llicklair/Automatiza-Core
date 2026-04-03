"""Asesoría Documental — Generación de documentos laborales con IA.

Endpoints:
  POST /hr/documents/generate  — Genera un borrador con LLM
  GET  /hr/documents           — Lista documentos generados del tenant
  GET  /hr/documents/{id}      — Detalle de un documento
  POST /hr/documents/{id}/approve — Marca como aprobado
  DELETE /hr/documents/{id}    — Elimina un borrador
"""
import uuid
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, Text, DateTime, JSON, select, desc
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
    doc_type = Column(String(50), nullable=False)       # contract, nda, termination, settlement, addendum, other
    title = Column(String(255), nullable=False)
    employee_name = Column(String(200), nullable=True)  # Optional employee target
    content_html = Column(Text, nullable=False)         # HTML rendered by LLM
    status = Column(String(20), default="draft")        # draft | approved
    instructions = Column(Text, nullable=True)          # User's original prompt
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    approved_at = Column(DateTime, nullable=True)


# ── Schemas ────────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    doc_type: str                    # contract, nda, termination, settlement, addendum, other
    instructions: str                # Free-text description of what to generate
    employee_name: str | None = None # Optional: auto-fill employee data
    employee_id: str | None = None   # Optional: pull data from HR module

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


# ── System Prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """Eres un asesor jurídico-laboral especializado en documentación de empresas españolas.
Generas documentos laborales profesionales en HTML limpio.

REGLAS ESTRICTAS:
1. El documento SIEMPRE es un BORRADOR que requiere revisión humana.
2. Incluye cabecera con "BORRADOR — PENDIENTE DE REVISIÓN" en rojo.
3. Usa formato profesional: encabezado con datos de las partes, cláusulas numeradas, pie con firmas.
4. La ley aplicable es SIEMPRE la legislación española vigente (Estatuto de los Trabajadores, etc).
5. Si faltan datos (NIF, dirección, etc), pon marcadores como [NIF_EMPRESA] para que el usuario los rellene.
6. Responde SOLO con el HTML del documento. Sin explicaciones fuera del HTML.
7. Usa etiquetas HTML semánticas: <h1>, <h2>, <p>, <ol>, <li>, <table>.
8. Añade clases CSS inline para un diseño profesional (colores neutros, márgenes).

TIPOS DE DOCUMENTO:
- contract: Contrato de trabajo (indefinido por defecto si no se especifica)
- nda: Acuerdo de confidencialidad / No divulgación
- termination: Carta de despido
- settlement: Finiquito / Liquidación de haberes
- addendum: Adenda a contrato existente
- other: Documento libre según instrucciones
"""


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_hr_document(
    payload: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera un borrador de documento laboral usando el LLM."""
    from langchain_core.messages import SystemMessage, HumanMessage
    from app.core.llm_factory import get_llm_for_tenant

    # Build context with employee data if provided
    employee_context = ""
    if payload.employee_id:
        try:
            from app.db.models.hr import HREmployee
            result = await db.execute(
                select(HREmployee).where(
                    HREmployee.id == payload.employee_id,
                    HREmployee.tenant_id == current_user.tenant_id,
                )
            )
            emp = result.scalar_one_or_none()
            if emp:
                employee_context = (
                    f"\nDatos del empleado:\n"
                    f"- Nombre: {emp.name}\n"
                    f"- DNI/NIE: {emp.nif or '[DNI_EMPLEADO]'}\n"
                    f"- Puesto: {emp.role or '[PUESTO]'}\n"
                    f"- Departamento: {emp.department or '[DEPARTAMENTO]'}\n"
                    f"- Salario bruto: {emp.base_salary or '[SALARIO]'}€/año\n"
                    f"- Fecha incorporación: {emp.join_date or '[FECHA_INICIO]'}\n"
                )
        except Exception as e:
            logger.warning("No se pudo cargar empleado %s: %s", payload.employee_id, e)

    # Tenant data for company header
    try:
        from app.db.models.tenant import Tenant
        result = await db.execute(
            select(Tenant).where(Tenant.id == current_user.tenant_id)
        )
        tenant = result.scalar_one_or_none()
        company_context = ""
        if tenant:
            company_context = (
                f"\nDatos de la empresa:\n"
                f"- Razón social: {tenant.name or '[NOMBRE_EMPRESA]'}\n"
                f"- CIF: {tenant.nif or '[CIF_EMPRESA]'}\n"
                f"- Dirección: {tenant.address or '[DIRECCIÓN_EMPRESA]'}\n"
            )
    except Exception:
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
        response = await llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        content_html = response.content
    except Exception as e:
        logger.error("Error generando documento: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar el documento: {str(e)}"
        )

    # Persist
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
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return {
        "id": str(doc.id),
        "title": doc.title,
        "doc_type": doc.doc_type,
        "content_html": doc.content_html,
        "status": doc.status,
        "created_at": doc.created_at.isoformat(),
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
    doc.approved_at = datetime.now(UTC)
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
