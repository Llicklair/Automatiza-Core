"""
Schemas Pydantic para el sistema de tareas IA.
StepResult es el tipo de retorno estándar que cada agente usa
para reportar el resultado de cada paso de ejecución.
"""
from typing import Any
from pydantic import BaseModel


class StepResult(BaseModel):
    step_id: str
    description: str
    status: str        # "completed" | "failed" | "pending"
    action_taken: str
    data: dict[str, Any] | None = None
    error: str | None = None
