from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# --- Workflows ---


class WorkflowBase(BaseModel):
    name: str = Field(..., description="Nombre descriptivo de la regla o workflow")
    description: str | None = None
    is_active: bool = True
    trigger_type: str = Field(..., description="Tipo de trigger: event_based, schedule_based, manual")
    trigger_config: dict[str, Any] = Field(default_factory=dict, description="Configuración del trigger")
    action_type: str = Field(..., description="Tipo de acción: create_task, webhook, email")
    action_config: dict[str, Any] = Field(default_factory=dict, description="Configuración de la acción a realizar")
    ui_nodes: list[dict[str, Any]] | None = Field(default=None, description="Topología visual de nodos del grafo")
    ui_edges: list[dict[str, Any]] | None = Field(default=None, description="Conexiones visuales del grafo")
    execution_mode: str = Field(
        default="reasoning",
        description="Modo de ejecución: 'reasoning' (LLM interpreta en tiempo real) o 'deterministic' (pasos precompilados)",
    )


class WorkflowCreate(WorkflowBase):
    compiled_steps: list[dict[str, Any]] | None = None


class WorkflowParseRequest(BaseModel):
    text: str = Field(..., description="Instrucción en lenguaje natural")


class WorkflowParseResponse(BaseModel):
    name: str
    description: str | None = None
    trigger_type: str
    trigger_config: dict[str, Any]
    action_type: str
    action_config: dict[str, Any]
    ui_nodes: list[dict[str, Any]] | None = None
    ui_edges: list[dict[str, Any]] | None = None
    can_be_deterministic: bool = False
    determinism_question: str | None = None


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    trigger_type: str | None = None
    trigger_config: dict[str, Any] | None = None
    action_type: str | None = None
    action_config: dict[str, Any] | None = None
    execution_mode: str | None = None
    compiled_steps: list[dict[str, Any]] | None = None


class WorkflowResponse(WorkflowBase):
    id: UUID
    tenant_id: UUID
    created_by: UUID | None = None
    compiled_steps: list[dict[str, Any]] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Workflow Executions ---


class WorkflowExecutionBase(BaseModel):
    workflow_id: UUID
    status: str = Field(default="pending")
    trigger_payload: dict[str, Any] | None = None


class WorkflowExecutionResponse(WorkflowExecutionBase):
    id: UUID
    tenant_id: UUID
    task_id: UUID | None = None
    result_log: str | None = None
    node_states: dict[str, Any] | None = None
    current_node_id: str | None = None
    paused_at: datetime | None = None
    started_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
