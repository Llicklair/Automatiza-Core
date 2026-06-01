"""Schemas Pydantic para empleados IA y activity feed."""

from pydantic import BaseModel, ConfigDict, Field


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

    # Contrato custom (4 capacidades). Para builtins siempre vacíos / False.
    scope: dict | None = None
    memory_enabled: bool = False
    knowledge_enabled: bool = False
    workflows: list[dict] | None = None

    model_config = ConfigDict(from_attributes=True)


class AIEmployeeCreate(BaseModel):
    """Alta de empleado IA custom.

    El servicio aplica el contrato "≥2 de 4 capacidades" para que el
    empleado justifique existir frente a un default + system_prompt
    addendum. Si no se cumple, la ruta responde 422 con la indicación de
    crear un "Perfil" en su lugar.
    """

    name: str
    role_description: str
    budget_limit_usd: float = 10.0

    scope: dict | None = Field(
        default=None,
        description="Filtro persistente: {clients, categories, filters}.",
    )
    memory_enabled: bool = False
    knowledge_enabled: bool = False
    workflows: list[dict] | None = Field(
        default=None,
        description="Rutinas: [{name, cron, steps}].",
    )


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


class AIEmployeeBudgetUpdate(BaseModel):
    """Actualiza el tope de gasto mensual. `null` = sin límite."""

    budget_limit_usd: float | None = Field(default=None, ge=0)


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
