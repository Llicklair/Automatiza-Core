"""
Endpoints para gestión de reclutamiento.
GET/POST puestos, GET candidatos, POST upload CV, PATCH estado candidato.
"""

import logging
import os
import shutil
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.hr import Candidate, RecruitmentPosition
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = os.environ.get("CV_UPLOAD_DIR", "uploads/cvs")


# ── Schemas ──────────────────────────────────────────────────────────────────


class PositionCreate(BaseModel):
    title: str
    department: str = ""
    description: str = ""
    required_skills: list[str] = []
    experience_min_years: float = 0
    salary_range_min: float | None = None
    salary_range_max: float | None = None


class PositionResponse(BaseModel):
    id: UUID
    title: str
    department: str | None
    description: str | None
    required_skills: list[str] | None
    experience_min_years: float | None
    salary_range_min: float | None
    salary_range_max: float | None
    status: str
    candidate_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CandidateResponse(BaseModel):
    id: UUID
    position_id: UUID | None
    name: str
    email: str | None
    phone: str | None
    skills: list[str] | None
    experience_years: float | None
    languages: list | None
    education: str | None
    summary: str | None
    score: float | None
    score_breakdown: dict | None
    status: str
    cv_file_path: str | None

    model_config = ConfigDict(from_attributes=True)


class StatusUpdate(BaseModel):
    status: str


# ── Positions ────────────────────────────────────────────────────────────────


@router.get("/positions", response_model=list[PositionResponse])
@limiter.limit("30/minute")
async def list_positions(
    request: Request,
    status_filter: str = "all",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(RecruitmentPosition).where(RecruitmentPosition.tenant_id == current_user.tenant_id)
    if status_filter != "all":
        q = q.where(RecruitmentPosition.status == status_filter)

    result = await db.execute(q.order_by(RecruitmentPosition.created_at.desc()))
    positions = result.scalars().all()

    # Contar candidatos por puesto
    count_q = (
        select(Candidate.position_id, func.count(Candidate.id))
        .where(Candidate.tenant_id == current_user.tenant_id)
        .group_by(Candidate.position_id)
    )
    count_result = await db.execute(count_q)
    counts = dict(count_result.all())

    out = []
    for p in positions:
        d = {
            "id": p.id,
            "title": p.title,
            "department": p.department,
            "description": p.description,
            "required_skills": p.required_skills,
            "experience_min_years": float(p.experience_min_years) if p.experience_min_years else 0,
            "salary_range_min": float(p.salary_range_min) if p.salary_range_min else None,
            "salary_range_max": float(p.salary_range_max) if p.salary_range_max else None,
            "status": p.status,
            "candidate_count": counts.get(p.id, 0),
        }
        out.append(d)
    return out


@router.post("/positions", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_position(
    request: Request,
    payload: PositionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pos = RecruitmentPosition(
        tenant_id=current_user.tenant_id,
        title=payload.title,
        department=payload.department,
        description=payload.description,
        required_skills=payload.required_skills,
        experience_min_years=payload.experience_min_years,
        salary_range_min=payload.salary_range_min,
        salary_range_max=payload.salary_range_max,
    )
    db.add(pos)
    await db.commit()
    await db.refresh(pos)
    return {
        **{c.name: getattr(pos, c.name) for c in pos.__table__.columns},
        "experience_min_years": float(pos.experience_min_years) if pos.experience_min_years else 0,
        "candidate_count": 0,
    }


# ── Candidates ───────────────────────────────────────────────────────────────


@router.get("/positions/{position_id}/candidates", response_model=list[CandidateResponse])
@limiter.limit("30/minute")
async def list_candidates(
    request: Request,
    position_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Candidate)
        .where(
            Candidate.tenant_id == current_user.tenant_id,
            Candidate.position_id == position_id,
        )
        .order_by(Candidate.score.desc().nullslast())
    )
    return result.scalars().all()


@router.post("/positions/{position_id}/upload-cv", response_model=CandidateResponse)
@limiter.limit("10/minute")
async def upload_cv(
    request: Request,
    position_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Sube un CV (PDF), lo parsea con IA, puntúa y guarda el candidato."""
    # Verificar que el puesto existe
    pos_result = await db.execute(
        select(RecruitmentPosition).where(
            RecruitmentPosition.id == position_id,
            RecruitmentPosition.tenant_id == current_user.tenant_id,
        )
    )
    position = pos_result.scalars().first()
    if not position:
        raise HTTPException(status_code=404, detail="Puesto no encontrado")

    # Guardar archivo
    tenant_dir = os.path.join(UPLOAD_DIR, str(current_user.tenant_id))
    os.makedirs(tenant_dir, exist_ok=True)
    file_id = str(uuid4())
    ext = os.path.splitext(file.filename or "cv.pdf")[1] or ".pdf"
    file_path = os.path.join(tenant_dir, f"{file_id}{ext}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parsear y puntuar
    from app.services.cv_parser import extract_cv_data, parse_cv_file, score_candidate

    cv_text = await parse_cv_file(file_path)
    if not cv_text:
        raise HTTPException(status_code=422, detail="No se pudo extraer texto del PDF")

    cv_data = await extract_cv_data(cv_text)

    pos_data = {
        "title": position.title,
        "department": position.department,
        "required_skills": position.required_skills or [],
        "experience_min_years": float(position.experience_min_years or 0),
    }
    scoring = await score_candidate(cv_data, pos_data)

    candidate = Candidate(
        tenant_id=current_user.tenant_id,
        position_id=position_id,
        name=cv_data.get("name") or file.filename or "Candidato",
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


@router.patch("/candidates/{candidate_id}/status", response_model=CandidateResponse)
@limiter.limit("30/minute")
async def update_candidate_status(
    request: Request,
    candidate_id: UUID,
    payload: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    valid = {"new", "reviewed", "shortlisted", "rejected", "hired"}
    if payload.status not in valid:
        raise HTTPException(
            status_code=400, detail=f"Estado inválido. Opciones: {', '.join(valid)}"
        )

    result = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == current_user.tenant_id,
        )
    )
    c = result.scalars().first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")

    c.status = payload.status
    await db.commit()
    await db.refresh(c)
    return c


@router.post("/analyze-cv")
@limiter.limit("10/minute")
async def analyze_cv_standalone(
    request: Request,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """Analiza un CV sin asociarlo a ningún puesto. Devuelve datos extraídos por IA."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    tmp_path = f"/tmp/cv_standalone_{uuid4().hex}.pdf"
    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        from app.services.cv_parser import extract_cv_data, parse_cv_file

        cv_text = await parse_cv_file(tmp_path)
        if not cv_text.strip():
            raise HTTPException(status_code=422, detail="No se pudo extraer texto del PDF")

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
