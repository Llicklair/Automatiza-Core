"""Schemas Pydantic para empleados IA y activity feed."""

from pydantic import BaseModel, ConfigDict


class AIEmployeeOut(BaseModel):
    id: str
    name: str
    role: str
    domain: str
    status: str
    is_builtin: bool
    budget_limit_usd: float | None
    doc_folder: str | None = None
    icon: str | None = None
    avatar_color: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AIEmployeeCreate(BaseModel):
    name: str
    role_description: str
    budget_limit_usd: float = 10.0


class AIEmployeeProvision(BaseModel):
    domain: str | None = None
    role: str | None = None
    system_prompt: str | None = None
    doc_folder: str | None = None
    skills: list[str] = []


class AIEmployeeIconUpdate(BaseModel):
    icon: str


class AIEmployeeAppearanceUpdate(BaseModel):
    icon: str | None = None
    avatar_color: str | None = None


class InstructPayload(BaseModel):
    message: str


class ActivityEntryOut(BaseModel):
    id: str
    employee_id: str | None
    category: str
    icon: str
    message: str
    metadata: dict | None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ActivityEntryCreate(BaseModel):
    category: str
    message: str
    icon: str = "📋"
    employee_id: str | None = None
    task_id: str | None = None
    metadata: dict | None = None
