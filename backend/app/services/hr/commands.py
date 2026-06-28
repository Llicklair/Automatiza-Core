"""HR commands - write operations (CQRS-lite).

All functions here produce side effects: INSERT/UPDATE/DELETE or file writes.
Read helpers are imported from queries.py to avoid duplication.
"""

import asyncio
import logging
import os
import shutil
import tempfile
import uuid as uuid_mod
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import local_today
from app.db.models.hr import (
    Attendance,
    Candidate,
    Expense,
    LeaveRequest,
    RecruitmentPosition,
    WorkSchedule,
)
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


# â"€â"€ Employee commands â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€


async def create_employee(data: dict, tenant_id, db: AsyncSession) -> Employee:
    """Crea empleado con dedup de NIF y emite evento.

    Normaliza el NIF (strip + uppercase) y valida unicidad case-insensitive
    por tenant. La BD tiene un partial UNIQUE INDEX (tenant_id, UPPER(nif))
    como segunda barrera ante race conditions.

    Raises:
        ValueError: si ya existe un empleado con el mismo NIF.
    """
    from sqlalchemy import func
    from sqlalchemy.exc import IntegrityError

    data = dict(data)
    normalized_nif = (data.get("nif") or "").strip().upper() or None
    data["nif"] = normalized_nif

    if normalized_nif:
        result = await db.execute(
            select(Employee).where(
                Employee.tenant_id == tenant_id,
                func.upper(Employee.nif) == normalized_nif,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(
                f"Ya existe un empleado con NIF {normalized_nif}: "
                f"{existing.name} (ID: {existing.id})"
            )

    emp = Employee(tenant_id=tenant_id, **data)
    db.add(emp)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError(
            f"Ya existe un empleado con NIF {normalized_nif} en el sistema "
            f"(detectado por restricción de unicidad de BD)."
        ) from None
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
                "nif": emp.nif,
            },
        )
    except Exception:
        logger.warning("emit_event employee_created fallo - no es critico")

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
    from sqlalchemy.exc import IntegrityError

    from app.core.exceptions import ConflictError

    emp = await get_employee(employee_id, tenant_id, db)
    if not emp:
        return False
    try:
        await db.delete(emp)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(
            "No se puede eliminar el empleado porque tiene registros asociados "
            "(nóminas, fichajes, etc.)"
        ) from None
    return True


# â"€â"€ Document commands â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€


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
        title += f" - {employee_name}"

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

    # R2: guardar con el `db` inyectado (atómico con la request), no con una sesión
    # aparte. `refresh` recarga id/doc_number/created_at sin lazy-load — mismo patrón
    # que create_invoice/create_payroll.
    try:
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
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
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
        "doc_number": doc.doc_number,
        "instructions": doc.instructions,
        "created_at": doc.created_at.isoformat(),
        "approved_at": None,
    }


async def _next_doc_number(db: AsyncSession, tenant_id, year: int) -> str:
    """Siguiente folio correlativo de gestoría para (tenant, año): DOC-{año}-{NNNN}.

    El padding a 4 dígitos hace que MAX() lexicográfico = máximo numérico dentro
    del mismo año. Advisory lock en PostgreSQL para evitar colisiones; SQLite es
    single-writer. El caller debe estar en una transacción abierta.
    """
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"hrdoc:{tenant_id}:{year}"},
        )
    prefix = f"DOC-{year}-"
    res = await db.execute(
        select(func.max(HRDocument.doc_number)).where(
            HRDocument.tenant_id == tenant_id,
            HRDocument.doc_number.like(f"{prefix}%"),
        )
    )
    last = res.scalar()
    seq = (int(last.rsplit("-", 1)[-1]) + 1) if last else 1
    return f"{prefix}{seq:04d}"


async def approve_document(doc_id: str, tenant_id, db: AsyncSession) -> dict:
    """Mark a document as approved. Raises ValueError if not found.

    Al aprobar por primera vez se asigna un folio correlativo de gestoría
    (`doc_number`) para trazabilidad y referencia legal.
    """
    result = await db.execute(
        select(HRDocument).where(
            HRDocument.id == doc_id,
            HRDocument.tenant_id == tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError("Documento no encontrado")

    # Idempotencia: una 2a aprobacion (doble-click/reintento) NO debe re-escribir
    # `approved_at` —perderia la hora REAL de aprobacion en la traza legal— ni
    # re-tocar el folio. Si ya esta aprobado, devuelve el estado actual sin mutar.
    if doc.status == "approved":
        return {
            "id": str(doc.id),
            "status": "approved",
            "approved_at": doc.approved_at.isoformat() if doc.approved_at else None,
            "doc_number": doc.doc_number,
        }

    doc.status = "approved"
    doc.approved_at = datetime.now(UTC)
    if not doc.doc_number:
        doc.doc_number = await _next_doc_number(db, tenant_id, doc.approved_at.year)
    await db.commit()
    return {
        "id": str(doc.id),
        "status": "approved",
        "approved_at": doc.approved_at.isoformat(),
        "doc_number": doc.doc_number,
    }


def _render_hr_document_pdf(doc: HRDocument) -> bytes:
    """Renderiza el `content_html` de un documento de gestoría a PDF (xhtml2pdf).

    Incluye el folio (`doc_number`) en una cabecera discreta para trazabilidad.
    Estos bytes sirven tanto para descarga como para firma con AutoFirma
    (`/signing/autofirma/init` acepta el documento en base64).
    """
    import html as _html
    import io

    try:
        from xhtml2pdf import pisa
    except ImportError as e:  # pragma: no cover - dependencia de entorno
        raise RuntimeError("Falta xhtml2pdf para generar el PDF: " + str(e)) from e

    folio = doc.doc_number or "BORRADOR (sin aprobar)"
    header = _html.escape(f"Folio: {folio} · {doc.title}")
    full_html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
        "<style>"
        "@page { size: A4; margin: 2.2cm 2cm; }"
        "body { font-family: Helvetica, Arial, sans-serif; font-size: 11px; color: #1a1a1a; }"
        "table { width: 100%; border-collapse: collapse; }"
        "td, th { border: 1px solid #ddd; padding: 4px; }"
        "h1 { font-size: 18px; } h2 { font-size: 14px; }"
        ".gestoria-folio { font-size: 8px; color: #888; border-bottom: 1px solid #eee;"
        " padding-bottom: 4px; margin-bottom: 12px; }"
        "</style></head><body>"
        f'<div class="gestoria-folio">{header}</div>'
        f"{doc.content_html or ''}"
        "</body></html>"
    )
    buffer = io.BytesIO()
    status = pisa.CreatePDF(full_html, dest=buffer, encoding="utf-8")
    if status.err:
        raise RuntimeError(f"xhtml2pdf falló al generar el PDF ({status.err} errores)")
    return buffer.getvalue()


async def get_document_pdf(doc_id, tenant_id, db: AsyncSession) -> tuple[bytes, str]:
    """Devuelve (pdf_bytes, filename) de un documento de gestoría. ValueError si no existe."""
    result = await db.execute(
        select(HRDocument).where(
            HRDocument.id == doc_id,
            HRDocument.tenant_id == tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError("Documento no encontrado")
    pdf = _render_hr_document_pdf(doc)
    base = (doc.doc_number or doc.title or "documento").replace("/", "-").replace(" ", "_")
    return pdf, f"{base}.pdf"


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


# â"€â"€ Recruitment commands â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€


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
    """Parse a CV PDF and persist the candidate.

    NO realiza scoring automático del candidato — la evaluación de mérito es
    responsabilidad humana del recruiter (cumplimiento Anexo III AI Act,
    Reglamento UE 2024/1689). Ver `docs/ai_act_scoping.md`.
    """
    # AI.SCO — `score_candidate` no se invoca.
    from app.services.ai.cv_parser import extract_cv_data, parse_cv_file

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
    # No se admiten CVs en un puesto CERRADO: crearia un Candidate bajo un
    # proceso ya finalizado (backlog huerfano filtrado de las vistas de puestos
    # abiertos que ningun reclutador gestionara). 'paused' SI se permite (puede
    # seguir recibiendo CVs para cuando se reactive). Corta ANTES de escribir el
    # fichero a disco.
    if position.status == "closed":
        raise ValueError("El puesto está cerrado y no admite nuevas candidaturas")

    # Save file
    tenant_dir = os.path.join(UPLOAD_DIR_CVS, str(tenant_id))
    os.makedirs(tenant_dir, exist_ok=True)
    file_id = str(uuid4())
    ext = os.path.splitext(file_name or "cv.pdf")[1] or ".pdf"
    file_path = os.path.join(tenant_dir, f"{file_id}{ext}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file_obj, f)

    # Parse only (no scoring)
    cv_text = await parse_cv_file(file_path)
    if not cv_text:
        raise ValueError("No se pudo extraer texto del PDF")

    cv_data = await extract_cv_data(cv_text)

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

    # Directorio temporal del SO (cross-platform: no existe `/tmp` en Windows).
    tmp_path = os.path.join(tempfile.gettempdir(), f"cv_standalone_{uuid4().hex}.pdf")
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


# ── Schedule commands ─────────────────────────────────────────────────────────


async def upsert_schedule(
    db: AsyncSession, tenant_id, employee_id: UUID, schedules: list[dict]
) -> list[WorkSchedule]:
    """Replace all schedule rows for an employee (upsert by day_of_week)."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    for s in schedules:
        stmt = (
            pg_insert(WorkSchedule)
            .values(
                employee_id=employee_id,
                tenant_id=tenant_id,
                day_of_week=s["day_of_week"],
                start_time=s["start_time"],
                end_time=s["end_time"],
                active=s.get("active", True),
            )
            .on_conflict_do_update(
                index_elements=["employee_id", "day_of_week"],
                set_={
                    "start_time": s["start_time"],
                    "end_time": s["end_time"],
                    "active": s.get("active", True),
                },
            )
        )
        await db.execute(stmt)
    await db.commit()
    result = await db.execute(
        select(WorkSchedule)
        .where(WorkSchedule.employee_id == employee_id, WorkSchedule.tenant_id == tenant_id)
        .order_by(WorkSchedule.day_of_week)
    )
    return list(result.scalars().all())


# ── Attendance commands ───────────────────────────────────────────────────────


async def clock_in(
    db: AsyncSession, tenant_id, employee_id: UUID, notes: str | None = None
) -> Attendance:
    """Create an attendance clock-in. Raises ValueError if already open."""

    existing = await db.execute(
        select(Attendance).where(
            Attendance.employee_id == employee_id,
            Attendance.tenant_id == tenant_id,
            Attendance.clock_out.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("El empleado ya tiene una entrada abierta")

    record = Attendance(
        tenant_id=tenant_id,
        employee_id=employee_id,
        date=local_today(),
        notes=notes,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def clock_out_attendance(db: AsyncSession, tenant_id, attendance_id: UUID) -> Attendance:
    """Set clock_out = now() and auto-create JornadaRecord for legal compliance."""
    from app.db.models.hr import JornadaRecord

    result = await db.execute(
        select(Attendance).where(
            Attendance.id == attendance_id,
            Attendance.tenant_id == tenant_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError("Fichaje no encontrado")
    if record.clock_out is not None:
        raise ValueError("Este fichaje ya tiene salida registrada")

    now = datetime.now(UTC)
    record.clock_out = now
    await db.commit()
    await db.refresh(record)

    # Auto-generate JornadaRecord (RD 8/2019)
    try:
        hora_entrada = record.clock_in.astimezone(UTC).strftime("%H:%M")
        hora_salida = now.strftime("%H:%M")
        mins = (now - record.clock_in).total_seconds() / 60
        horas = round(mins / 60, 2)

        jornada = JornadaRecord(
            tenant_id=tenant_id,
            employee_id=record.employee_id,
            fecha=record.date,
            hora_entrada=hora_entrada,
            hora_salida=hora_salida,
            horas_ordinarias=min(horas, 8.0),
            horas_extra=max(0, round(horas - 8.0, 2)),
            year=record.date.year,
            month=record.date.month,
            notas=record.notes or "",
        )
        db.add(jornada)
        await db.commit()
    except Exception:
        # non-critical — don't fail the clock-out
        logger.exception("No se pudo guardar el registro de jornada; el fichaje se mantiene")

    return record


# ── Leave request commands ────────────────────────────────────────────────────


async def _ws_notify(tenant_id, message: str, notif_type: str = "info") -> None:
    try:
        from app.api.ws.notifications import manager
        from app.core.background import spawn
        spawn(
            manager.broadcast_to_tenant(
                str(tenant_id),
                {"type": "hr_notification", "message": message, "notif_type": notif_type},
            )
        )
    except Exception:
        logger.debug("No se pudo emitir la notificación WS de RRHH; continúo", exc_info=True)


async def create_leave_request(
    db: AsyncSession, tenant_id, employee_id: UUID,
    leave_type: str, start_date, end_date, notes: str | None = None,
) -> LeaveRequest:
    req = LeaveRequest(
        tenant_id=tenant_id,
        employee_id=employee_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        notes=notes,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    await _ws_notify(tenant_id, "Nueva solicitud de ausencia pendiente de aprobación", "info")
    return req


async def approve_leave_request(db: AsyncSession, tenant_id, request_id: UUID) -> LeaveRequest:
    """Approve a leave request and update employee status."""
    req = await _get_leave_request(db, tenant_id, request_id)
    # Idempotencia + maquina de estados: solo se decide una solicitud PENDIENTE.
    # Sin este guard, un doble-click re-escribia emp.status/leave_* (benigno) y,
    # peor, aprobar→rechazar dejaba emp.status="leave" HUERFANO (el reject no
    # revierte el estado del empleado) → el empleado figuraba de baja para
    # siempre pese a la solicitud rechazada. Deshacer una decision ya tomada es
    # un flujo aparte (reopen) que debe revertir emp.status → inbox.
    if req.status != "pending":
        raise ValueError(f"La solicitud ya está '{req.status}'; no se puede aprobar de nuevo")
    req.status = "approved"
    emp = await get_employee(req.employee_id, tenant_id, db)
    if emp:
        emp.status = "leave"
        emp.leave_type = req.leave_type
        emp.leave_start = req.start_date
        emp.leave_end = req.end_date
    await db.commit()
    await db.refresh(req)
    name = emp.name if emp else "Empleado"
    await _ws_notify(tenant_id, f"Solicitud aprobada: {name} de baja desde {req.start_date}", "success")
    return req


async def reject_leave_request(db: AsyncSession, tenant_id, request_id: UUID) -> LeaveRequest:
    req = await _get_leave_request(db, tenant_id, request_id)
    # Idempotencia + maquina de estados: solo se rechaza una solicitud PENDIENTE.
    # Rechazar una YA APROBADA dejaba emp.status="leave" huerfano (este reject no
    # revierte el estado del empleado). Deshacer una aprobacion = flujo reopen
    # aparte (debe revertir emp.status/leave_*) → inbox.
    if req.status != "pending":
        raise ValueError(f"La solicitud ya está '{req.status}'; no se puede rechazar")
    req.status = "rejected"
    await db.commit()
    await db.refresh(req)
    await _ws_notify(tenant_id, "Solicitud de ausencia rechazada", "warning")
    return req


async def delete_leave_request(db: AsyncSession, tenant_id, request_id: UUID) -> None:
    req = await _get_leave_request(db, tenant_id, request_id)
    await db.delete(req)
    await db.commit()


async def _get_leave_request(db: AsyncSession, tenant_id, request_id: UUID) -> LeaveRequest:
    result = await db.execute(
        select(LeaveRequest).where(LeaveRequest.id == request_id, LeaveRequest.tenant_id == tenant_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise ValueError("Solicitud no encontrada")
    return req


# ── Expense commands ──────────────────────────────────────────────────────────


async def create_expense(
    db: AsyncSession, tenant_id, employee_id: UUID,
    amount: float, category: str, description: str, date, notes: str | None = None,
) -> Expense:
    exp = Expense(
        tenant_id=tenant_id,
        employee_id=employee_id,
        amount=amount,
        category=category,
        description=description,
        date=date,
        notes=notes,
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    await _ws_notify(tenant_id, f"Nuevo gasto de {amount:.2f}€ pendiente de aprobación", "info")
    return exp


async def approve_expense(db: AsyncSession, tenant_id, expense_id: UUID) -> Expense:
    exp = await _get_expense(db, tenant_id, expense_id)
    # Maquina de estados del gasto (pending → approved/rejected; approved →
    # reimbursed; rejected/reimbursed terminales). Solo se aprueba un PENDIENTE:
    # sin este guard se podia re-aprobar un gasto ya rechazado o ya REEMBOLSADO
    # (re-abriendo un gasto pagado) — corrompe el registro financiero. Idempotente.
    if exp.status != "pending":
        raise ValueError(f"Solo se puede aprobar un gasto pendiente (estado actual: '{exp.status}')")
    exp.status = "approved"
    await db.commit()
    await db.refresh(exp)
    await _ws_notify(tenant_id, f"Gasto de {float(exp.amount):.2f}€ aprobado", "success")
    return exp


async def reject_expense(db: AsyncSession, tenant_id, expense_id: UUID) -> Expense:
    exp = await _get_expense(db, tenant_id, expense_id)
    # Solo se rechaza un gasto PENDIENTE: sin guard se podia rechazar un gasto
    # ya APROBADO o ya REEMBOLSADO (marcar como rechazado algo ya pagado).
    if exp.status != "pending":
        raise ValueError(f"Solo se puede rechazar un gasto pendiente (estado actual: '{exp.status}')")
    exp.status = "rejected"
    await db.commit()
    await db.refresh(exp)
    await _ws_notify(tenant_id, f"Gasto de {float(exp.amount):.2f}€ rechazado", "warning")
    return exp


async def reimburse_expense(db: AsyncSession, tenant_id, expense_id: UUID) -> Expense:
    exp = await _get_expense(db, tenant_id, expense_id)
    # Solo se reembolsa un gasto APROBADO: sin guard se podia marcar "reembolsado"
    # (= registro de que se pagó al empleado) un gasto PENDIENTE (saltando la
    # aprobacion) o RECHAZADO (pagar algo rechazado), e idempotente frente a
    # doble-reembolso.
    if exp.status != "approved":
        raise ValueError(f"Solo se puede reembolsar un gasto aprobado (estado actual: '{exp.status}')")
    exp.status = "reimbursed"
    await db.commit()
    await db.refresh(exp)
    await _ws_notify(tenant_id, f"Gasto de {float(exp.amount):.2f}€ marcado como reembolsado", "success")
    return exp


async def upload_expense_receipt(
    db: AsyncSession, tenant_id, expense_id: UUID, file_bytes: bytes, filename: str
) -> Expense:
    exp = await _get_expense(db, tenant_id, expense_id)
    subdir = os.path.join(UPLOAD_DIR, "gastos", str(expense_id))
    os.makedirs(subdir, exist_ok=True)
    safe_name = f"{uuid_mod.uuid4().hex[:8]}_{Path(filename).name}"
    dest = os.path.join(subdir, safe_name)
    await asyncio.to_thread(Path(dest).write_bytes, file_bytes)
    exp.receipt_filename = filename
    exp.receipt_path = dest
    await db.commit()
    await db.refresh(exp)
    return exp


async def delete_expense(db: AsyncSession, tenant_id, expense_id: UUID) -> None:
    exp = await _get_expense(db, tenant_id, expense_id)
    if exp.receipt_path and os.path.exists(exp.receipt_path):
        try:
            shutil.rmtree(os.path.dirname(exp.receipt_path), ignore_errors=True)
        except Exception:
            logger.debug("No se pudo borrar el recibo en disco; continúo con el borrado del gasto", exc_info=True)
    await db.delete(exp)
    await db.commit()


async def _get_expense(db: AsyncSession, tenant_id, expense_id: UUID) -> Expense:
    result = await db.execute(
        select(Expense).where(Expense.id == expense_id, Expense.tenant_id == tenant_id)
    )
    exp = result.scalar_one_or_none()
    if not exp:
        raise ValueError("Gasto no encontrado")
    return exp


# ── Re-exports from sub-modules ───────────────────────────────────────────────

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
