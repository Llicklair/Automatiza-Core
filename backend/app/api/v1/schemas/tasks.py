"""Schemas Pydantic para Tasks, AuditLog y Aprobaciones."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# Re-export para compatibilidad — la fuente canónica es agents.types
from app.agents.types import StepResult  # noqa: F401

# ─── Tasks ───────────────────────────────────────────────────────────────────


class TaskCreate(BaseModel):
    # domain se persiste en Task.domain = String(100) → tope = longitud real
    # de la columna para evitar un INSERT que reviente en BD (500 no manejado).
    domain: str = Field(max_length=100)
    # user_intent se embebe en el prompt del agente LLM. Sin tope, un payload
    # multi-MB = DoS de coste. Cap generoso (≈10KB / ~2500 tokens): no rompe
    # instrucciones legítimas (siempre texto corto de usuario en este endpoint;
    # los flujos internos de contexto acumulado NO construyen TaskCreate).
    user_intent: str = Field(max_length=10000)
    additional_metadata: dict | None = None
    parent_task_id: str | None = None


class TaskOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    status: str
    domain: str
    user_intent: str | None
    plan: Any | None
    agent_results: Any | None = None
    current_step: int
    requires_human_approval: bool
    error_message: str | None
    additional_metadata: Any | None = None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


# ─── Audit Log ───────────────────────────────────────────────────────────────


class AuditLogOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    task_id: UUID | None
    tenant_id: UUID
    agent_name: str
    action_type: str
    input_data: Any | None
    output_data: Any | None
    validation_result: Any | None
    status: str
    error_detail: str | None
    executed_at: datetime
    # Nota: llm_prompt y llm_response SÓLO se exponen a admins
    llm_prompt: str | None = None
    llm_response: str | None = None


# ─── Pending Approvals ───────────────────────────────────────────────────────


class ApprovalDecision(BaseModel):
    approved: bool
    rejection_reason: str | None = None


class PendingApprovalOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    task_id: UUID
    action_description: str
    action_payload: Any
    risk_level: str
    expires_at: datetime
    status: str
    created_at: datetime | None = None
