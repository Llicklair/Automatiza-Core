"""Pydantic schemas for recruitment endpoints."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
    # AI.SCO — `score` y `score_breakdown` no se exponen por cumplimiento
    # Anexo III AI Act. Ver `docs/ai_act_scoping.md`.
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
    status: str
    cv_file_path: str | None

    model_config = ConfigDict(from_attributes=True)


class StatusUpdate(BaseModel):
    status: str
