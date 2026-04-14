"""Business logic for recruitment: positions, candidates, CV parsing."""

import logging
import os
import shutil
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.hr import Candidate, RecruitmentPosition
from app.services.ai.cv_parser import extract_cv_data, parse_cv_file, score_candidate

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.environ.get("CV_UPLOAD_DIR", "uploads/cvs")

VALID_CANDIDATE_STATUSES = {"new", "reviewed", "shortlisted", "rejected", "hired"}


async def list_positions(
    db: AsyncSession, tenant_id: UUID, status_filter: str = "all"
) -> list[dict]:
    q = select(RecruitmentPosition).where(RecruitmentPosition.tenant_id == tenant_id)
    if status_filter != "all":
        q = q.where(RecruitmentPosition.status == status_filter)

    result = await db.execute(q.order_by(RecruitmentPosition.created_at.desc()))
    positions = result.scalars().all()

    count_q = (
        select(Candidate.position_id, func.count(Candidate.id))
        .where(Candidate.tenant_id == tenant_id)
        .group_by(Candidate.position_id)
    )
    count_result = await db.execute(count_q)
    counts = dict(count_result.all())

    out = []
    for p in positions:
        out.append(
            {
                "id": p.id,
                "title": p.title,
                "department": p.department,
                "description": p.description,
                "required_skills": p.required_skills,
                "experience_min_years": float(p.experience_min_years)
                if p.experience_min_years
                else 0,
                "salary_range_min": float(p.salary_range_min)
                if p.salary_range_min
                else None,
                "salary_range_max": float(p.salary_range_max)
                if p.salary_range_max
                else None,
                "status": p.status,
                "candidate_count": counts.get(p.id, 0),
            }
        )
    return out


async def create_position(
    db: AsyncSession, tenant_id: UUID, payload: dict
) -> dict:
    pos = RecruitmentPosition(tenant_id=tenant_id, **payload)
    db.add(pos)
    await db.commit()
    await db.refresh(pos)
    return {
        **{c.name: getattr(pos, c.name) for c in pos.__table__.columns},
        "experience_min_years": float(pos.experience_min_years)
        if pos.experience_min_years
        else 0,
        "candidate_count": 0,
    }


async def list_candidates(
    db: AsyncSession, tenant_id: UUID, position_id: UUID
) -> list:
    result = await db.execute(
        select(Candidate)
        .where(
            Candidate.tenant_id == tenant_id,
            Candidate.position_id == position_id,
        )
        .order_by(Candidate.score.desc().nullslast())
    )
    return list(result.scalars().all())


async def upload_cv(
    db: AsyncSession,
    tenant_id: UUID,
    position_id: UUID,
    file_name: str,
    file_obj,
) -> Candidate:
    """Parse a CV PDF, score the candidate, and persist."""
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
    tenant_dir = os.path.join(UPLOAD_DIR, str(tenant_id))
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
        raise ValueError(
            f"Estado invalido. Opciones: {', '.join(VALID_CANDIDATE_STATUSES)}"
        )

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
