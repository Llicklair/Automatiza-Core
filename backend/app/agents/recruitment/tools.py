"""
Recruitment agent — tools: gestión de puestos y candidatos.
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select

from app.agents.agent_tools.reports import create_pdf_report, create_pdf_text_report
from app.db.base import AsyncSessionLocal
from app.db.models.hr import Candidate, RecruitmentPosition

logger = logging.getLogger(__name__)


@tool
async def create_position(
    tenant_id: str,
    title: str,
    department: str = "",
    description: str = "",
    required_skills: str = "[]",
    experience_min_years: float = 0,
    salary_range_min: float = 0,
    salary_range_max: float = 0,
) -> str:
    """Crea un nuevo puesto abierto para reclutar.
    required_skills es un JSON array de strings, ej: '["Python", "SQL"]'
    """
    try:
        skills = (
            json.loads(required_skills) if isinstance(required_skills, str) else required_skills
        )
    except json.JSONDecodeError:
        skills = [s.strip() for s in required_skills.split(",") if s.strip()]

    async with AsyncSessionLocal() as db:
        pos = RecruitmentPosition(
            tenant_id=UUID(tenant_id),
            title=title,
            department=department,
            description=description,
            required_skills=skills,
            experience_min_years=experience_min_years,
            salary_range_min=salary_range_min if salary_range_min else None,
            salary_range_max=salary_range_max if salary_range_max else None,
        )
        db.add(pos)
        await db.commit()
        await db.refresh(pos)
        return json.dumps(
            {
                "id": str(pos.id),
                "title": pos.title,
                "department": pos.department,
                "required_skills": pos.required_skills,
                "status": pos.status,
            },
            ensure_ascii=False,
        )


@tool
async def list_positions(tenant_id: str, status: str = "open") -> str:
    """Lista los puestos abiertos del tenant. status: open|closed|paused|all"""
    async with AsyncSessionLocal() as db:
        q = select(RecruitmentPosition).where(RecruitmentPosition.tenant_id == UUID(tenant_id))
        if status != "all":
            q = q.where(RecruitmentPosition.status == status)
        result = await db.execute(q.order_by(RecruitmentPosition.created_at.desc()))
        positions = result.scalars().all()

    if not positions:
        return "No hay puestos abiertos."

    lines = []
    for p in positions:
        skills = ", ".join(p.required_skills or [])
        lines.append(
            f"- {p.title} ({p.department or 'Sin dept.'}) | Skills: {skills} | Estado: {p.status} | ID: {p.id}"
        )
    return "\n".join(lines)


@tool
async def process_cv(tenant_id: str, position_id: str, cv_file_path: str) -> str:
    """Procesa un CV (PDF): extrae datos estructurados y guarda el candidato.

    Esta tool NO puntúa ni clasifica candidatos por mérito o "fit" — esa función
    está deshabilitada en MVP por cumplimiento Anexo III del Reglamento UE 2024/1689
    (AI Act). La evaluación de candidatos es responsabilidad humana del recruiter.

    cv_file_path: ruta al archivo PDF del CV.
    position_id: UUID del puesto al que aplica.
    """
    # AI.SCO — `score_candidate` no se invoca; ver docs/ai_act_scoping.md §2.
    from app.services.ai.cv_parser import extract_cv_data, parse_cv_file

    cv_text = await parse_cv_file(cv_file_path)
    if not cv_text:
        return "Error: no se pudo extraer texto del PDF."

    cv_data = await extract_cv_data(cv_text)

    async with AsyncSessionLocal() as db:
        pos_result = await db.execute(
            select(RecruitmentPosition).where(
                RecruitmentPosition.id == UUID(position_id),
                RecruitmentPosition.tenant_id == UUID(tenant_id),
            )
        )
        position = pos_result.scalars().first()
        if not position:
            return f"Error: puesto {position_id} no encontrado."

    async with AsyncSessionLocal() as db:
        candidate = Candidate(
            tenant_id=UUID(tenant_id),
            position_id=UUID(position_id),
            name=cv_data.get("name") or "Nombre no detectado",
            email=cv_data.get("email"),
            phone=cv_data.get("phone"),
            skills=cv_data.get("skills", []),
            experience_years=cv_data.get("experience_years"),
            languages=cv_data.get("languages", []),
            education=cv_data.get("education"),
            summary=cv_data.get("summary"),
            raw_cv_text=cv_text[:10000],
            cv_file_path=cv_file_path,
            status="new",
        )
        db.add(candidate)
        await db.commit()
        await db.refresh(candidate)

    return json.dumps(
        {
            "candidate_id": str(candidate.id),
            "name": candidate.name,
            "email": candidate.email,
            "skills": candidate.skills,
            "experience_years": float(candidate.experience_years)
            if candidate.experience_years
            else None,
        },
        ensure_ascii=False,
    )


@tool
async def list_candidates(
    tenant_id: str,
    position_id: str = "",
    status: str = "all",
) -> str:
    """Lista candidatos. Filtra por puesto o estado. Orden cronológico inverso.

    NOTA AI Act: esta tool no rankea candidatos por puntuación o "fit". El orden
    es por fecha de aplicación (más reciente primero). La selección humana es
    responsabilidad del recruiter.
    """
    async with AsyncSessionLocal() as db:
        q = select(Candidate).where(Candidate.tenant_id == UUID(tenant_id))
        if position_id:
            q = q.where(Candidate.position_id == UUID(position_id))
        if status != "all":
            q = q.where(Candidate.status == status)
        result = await db.execute(q.order_by(Candidate.created_at.desc()))
        candidates = result.scalars().all()

    if not candidates:
        return "No hay candidatos que coincidan con los filtros."

    lines = []
    for c in candidates:
        skills = ", ".join((c.skills or [])[:5])
        lines.append(
            f"- {c.name} | Skills: {skills} | Estado: {c.status} | ID: {c.id}"
        )
    return "\n".join(lines)


@tool
async def update_candidate_status(tenant_id: str, candidate_id: str, new_status: str) -> str:
    """Mueve un candidato en el pipeline. new_status: new|reviewed|shortlisted|rejected|hired"""
    valid = {"new", "reviewed", "shortlisted", "rejected", "hired"}
    if new_status not in valid:
        return f"Estado inválido. Opciones: {', '.join(valid)}"

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Candidate).where(
                Candidate.id == UUID(candidate_id),
                Candidate.tenant_id == UUID(tenant_id),
            )
        )
        c = result.scalars().first()
        if not c:
            return f"Candidato {candidate_id} no encontrado."
        old = c.status
        c.status = new_status
        await db.commit()
        return f"Candidato {c.name}: {old} → {new_status}"


tools = [create_position, list_positions, process_cv, list_candidates, update_candidate_status, create_pdf_report, create_pdf_text_report]


# Defensa multi-tenant: envolver tools para forzar tenant_id del ContextVar
from app.agents.tenant_context import isolated as _isolated
tools = _isolated(tools)
