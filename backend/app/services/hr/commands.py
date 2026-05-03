"""HR commands — write operations (CQRS-lite).

All functions here produce side effects: INSERT/UPDATE/DELETE or file writes.
Read helpers are imported from queries.py to avoid duplication.
"""

import logging
import os
import shutil
import uuid as uuid_mod
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.hr import Candidate, RecruitmentPosition
from app.db.models.hr_documents import HRDocument
from app.db.models.models import Employee
from app.services.event_bus import emit_event
from app.services.hr.queries import (
    DOC_TYPE_LABELS,
    UPLOAD_DIR,
    VALID_CANDIDATE_STATUSES,
    _build_company_context,
    _build_employee_context,
    _get_system_prompt,
    _strip_markdown_wrapper,
    get_employee,
)

logger = logging.getLogger(__name__)

UPLOAD_DIR_CVS = os.environ.get("CV_UPLOAD_DIR", "uploads/cvs")


# ── Employee commands ────────────────────────────────────────────────────────


async def create_employee(payload, tenant_id, db: AsyncSession) -> Employee:
    """Crea empleado y emite evento. Lanza SQLAlchemyError si falla."""
    emp = Employee(tenant_id=tenant_id, **payload.model_dump())
    db.add(emp)
    await db.commit()
    await db.refresh(emp)

    try:
        await emit_event(
            db,
            tenant_id,
            None,
            "employee_created",
            {
                "employee_id": str(emp.id),
                "name": emp.name,
            },
        )
    except Exception:
        logger.warning("emit_event employee_created fallo — no es critico")

    return emp


async def update_employee(
    employee_id: UUID, payload, tenant_id, db: AsyncSession
) -> Employee | None:
    emp = await get_employee(employee_id, tenant_id, db)
    if not emp:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(emp, field, value)
    await db.commit()
    await db.refresh(emp)
    return emp


async def delete_employee(employee_id: UUID, tenant_id, db: AsyncSession) -> bool:
    emp = await get_employee(employee_id, tenant_id, db)
    if not emp:
        return False
    await db.delete(emp)
    await db.commit()
    return True


# ── Document commands ────────────────────────────────────────────────────────


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

        async with AsyncSessionLocal() as save_db:
            doc = HRDocument(
                id=uuid_mod.uuid4(),
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


async def approve_document(doc_id: str, tenant_id, db: AsyncSession) -> dict:
    """Mark a document as approved. Raises ValueError if not found."""
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


# ── Recruitment commands ─────────────────────────────────────────────────────


async def create_position(db: AsyncSession, tenant_id: UUID, payload: dict) -> dict:
    pos = RecruitmentPosition(tenant_id=tenant_id, **payload)
    db.add(pos)
    await db.commit()
    await db.refresh(pos)
    return {
        **{c.name: getattr(pos, c.name) for c in pos.__table__.columns},
        "experience_min_years": float(pos.experience_min_years) if pos.experience_min_years else 0,
        "candidate_count": 0,
    }


async def upload_cv(
    db: AsyncSession,
    tenant_id: UUID,
    position_id: UUID,
    file_name: str,
    file_obj,
) -> Candidate:
    """Parse a CV PDF, score the candidate, and persist."""
    from app.services.ai.cv_parser import extract_cv_data, parse_cv_file, score_candidate

    # Verify position exists
    pos_result = await db.execute(
        select(RecruitmentPosition).where(
            RecruitmentPosition.id == position_id,
            RecruitmentPosition.tenant_id == tenant_id,
        )
    )
    position = pos_result.scalars().first()
    if not position:
        raise LookupError("Puesto no encontrado")

    # Save file
    tenant_dir = os.path.join(UPLOAD_DIR_CVS, str(tenant_id))
    os.makedirs(tenant_dir, exist_ok=True)
    file_id = str(uuid4())
    ext = os.path.splitext(file_name or "cv.pdf")[1] or ".pdf"
    file_path = os.path.join(tenant_dir, f"{file_id}{ext}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file_obj, f)

    # Parse and score
    cv_text = await parse_cv_file(file_path)
    if not cv_text:
        raise ValueError("No se pudo extraer texto del PDF")

    cv_data = await extract_cv_data(cv_text)

    pos_data = {
        "title": position.title,
        "department": position.department,
        "required_skills": position.required_skills or [],
        "experience_min_years": float(position.experience_min_years or 0),
    }
    scoring = await score_candidate(cv_data, pos_data)

    candidate = Candidate(
        tenant_id=tenant_id,
        position_id=position_id,
        name=cv_data.get("name") or file_name or "Candidato",
        email=cv_data.get("email"),
        phone=cv_data.get("phone"),
        skills=cv_data.get("skills", []),
        experience_years=cv_data.get("experience_years"),
        languages=cv_data.get("languages", []),
        education=cv_data.get("education"),
        summary=cv_data.get("summary"),
        raw_cv_text=cv_text[:10000],
        cv_file_path=file_path,
        score=scoring.get("score", 0),
        score_breakdown=scoring.get("breakdown"),
        status="new",
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return candidate


async def update_candidate_status(
    db: AsyncSession, tenant_id: UUID, candidate_id: UUID, new_status: str
) -> Candidate:
    if new_status not in VALID_CANDIDATE_STATUSES:
        raise ValueError(f"Estado invalido. Opciones: {', '.join(VALID_CANDIDATE_STATUSES)}")

    result = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
        )
    )
    c = result.scalars().first()
    if not c:
        raise LookupError("Candidato no encontrado")

    c.status = new_status
    await db.commit()
    await db.refresh(c)
    return c


async def analyze_cv_standalone(file_name: str, file_obj) -> dict:
    """Analyze a CV without linking to a position."""
    from app.services.ai.cv_parser import extract_cv_data, parse_cv_file

    if not file_name or not file_name.lower().endswith(".pdf"):
        raise ValueError("Solo se aceptan archivos PDF")

    tmp_path = f"/tmp/cv_standalone_{uuid4().hex}.pdf"
    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file_obj, f)

        cv_text = await parse_cv_file(tmp_path)
        if not cv_text.strip():
            raise ValueError("No se pudo extraer texto del PDF")

        cv_data = await extract_cv_data(cv_text)
        return {
            "name": cv_data.get("name"),
            "email": cv_data.get("email"),
            "phone": cv_data.get("phone"),
            "skills": cv_data.get("skills", []),
            "experience_years": cv_data.get("experience_years"),
            "education": cv_data.get("education"),
            "languages": cv_data.get("languages", []),
            "summary": cv_data.get("summary"),
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ── Re-exports from sub-modules ──────────────────────────────────────────────

from app.services.hr._employee_docs import (  # noqa: E402, F401
    delete_employee_document,
    upload_employee_document,
)
from app.services.hr._payroll import (  # noqa: E402, F401
    approve_payroll,
    create_payroll,
    create_payroll_auto,
    delete_payroll,
    generate_and_save_payroll_pdf,
    update_payroll,
)
from app.services.hr._special_docs import (  # noqa: E402, F401
    generate_finiquito_pdf,
    generate_liquidacion_pdf,
    generate_registro_jornada,
)
