from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


def _check_date_range(model):
    """Valida que due_date no sea anterior a start_date (ambos presentes)."""
    if model.start_date is not None and model.due_date is not None and model.due_date < model.start_date:
        raise ValueError("due_date no puede ser anterior a start_date")
    return model


# --- Projects ---
class ProjectBase(BaseModel):
    name: str
    description: str | None = None
    budget: float = 0.0
    status: str = "active"
    client_id: UUID | None = None
    start_date: datetime | None = None
    due_date: datetime | None = None


class ProjectCreate(ProjectBase):
    _validate_dates = model_validator(mode="after")(_check_date_range)


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    budget: float | None = None
    status: str | None = None
    client_id: UUID | None = None
    start_date: datetime | None = None
    due_date: datetime | None = None

    _validate_dates = model_validator(mode="after")(_check_date_range)


class ProjectResponse(ProjectBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Project Tasks ---
class ProjectTaskBase(BaseModel):
    project_id: UUID | None = None  # None = tarea simple sin proyecto
    title: str
    description: str | None = None
    status: str = "todo"
    assignee_id: UUID | None = None
    start_date: datetime | None = None
    due_date: datetime | None = None


class ProjectTaskCreate(ProjectTaskBase):
    _validate_dates = model_validator(mode="after")(_check_date_range)


class ProjectTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    assignee_id: UUID | None = None
    start_date: datetime | None = None
    due_date: datetime | None = None

    _validate_dates = model_validator(mode="after")(_check_date_range)


class ProjectTaskResponse(ProjectTaskBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    project: ProjectResponse | None = None
    model_config = ConfigDict(from_attributes=True)
