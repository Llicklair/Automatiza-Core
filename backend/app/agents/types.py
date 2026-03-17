"""Tipos base compartidos por todos los agentes."""
from typing import Any
from pydantic import BaseModel


class StepResult(BaseModel):
    step_id: str
    description: str
    status: str        # "completed" | "failed" | "pending"
    action_taken: str
    data: dict[str, Any] | None = None
    error: str | None = None
