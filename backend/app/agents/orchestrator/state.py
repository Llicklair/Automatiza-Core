"""
Tipos de estado del orquestador.
Extraído de orchestrator.py para mejorar legibilidad y reutilización.
"""

from enum import Enum
from typing import Any, TypedDict


class TaskStatus(str, Enum):
    PENDING = "pending"
    CLASSIFYING = "classifying"
    PLANNING = "planning"
    VALIDATING = "validating"
    EXECUTING = "executing"
    AWAITING_APPROVAL = "awaiting_approval"
    DONE = "done"
    FAILED = "failed"


class SubTask(TypedDict):
    id: str
    agent: str  # billing | documents | compliance | hr
    action: str
    params: dict
    depends_on: list[str]
    status: str  # pending | done | failed


class AgentResult(TypedDict):
    subtask_id: str
    agent: str
    success: bool
    output: Any
    error: str | None


class OrchestratorState(TypedDict):
    # Identidad
    task_id: str
    tenant_id: str
    user_id: str

    # Intención
    user_intent: str
    current_intent: str | None
    classified_domain: str | None

    # Planificación
    plan: list[SubTask] | None
    current_step: int

    # Ejecución
    agent_results: list[AgentResult]

    # Control de flujo
    status: TaskStatus
    requires_human_approval: bool
    approval_id: str | None
    error_message: str | None

    # Metadatos
    iteration_count: int  # Protección anti-bucle infinito
    tenant_knowledge: list[dict]
    additional_metadata: dict[str, Any] | None


MAX_ITERATIONS = 20  # Límite duro

VALID_DOMAINS = {
    "billing",
    "documents",
    "compliance",
    "hr",
    "banking",
    "rag",
    "crm",
    "excel",
    "email",
    "coordinator",
    "workflow",
    "skill",
    "marketing",
    "recruitment",
    "accounting",
    "inventory",
    "report",
    "chat",
    "custom",
}
