"""Import/export YAML de workflows (F3.10).

Permite que el usuario:
  - **Exporte** un Workflow del tenant a YAML para compartirlo o
    guardarlo como copia de seguridad.
  - **Importe** un YAML pegado (de otro tenant o de un repositorio
    externo) como Workflow nuevo en su tenant.

El YAML respeta el shape del modelo `Workflow` pero excluye los campos
de identidad/auditoría: id, tenant_id, created_by, created_at,
updated_at, is_active (siempre se importa como False para que el
usuario revise antes de activar).

Estructura del YAML (campos top-level):

    name: "Cierre mensual"
    description: "Cierre del mes con cuadre + presentación 303"
    trigger_type: "cron"
    trigger_config: { cron: "0 9 1 * *" }
    action_type: "agent_sequence"
    action_config: { agents: ["accounting", "compliance"] }
    execution_mode: "deterministic"
    compiled_steps:
      - { step: "close_period",   agent: "accounting" }
      - { step: "build_303",      agent: "compliance" }
    tags: ["mensual", "fiscal"]
"""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workflows import Workflow


class WorkflowYamlError(ValueError):
    """YAML inválido o incompatible con el shape esperado."""


_EXPORTED_FIELDS = (
    "name",
    "description",
    "trigger_type",
    "trigger_config",
    "action_type",
    "action_config",
    "execution_mode",
    "compiled_steps",
)
_REQUIRED_FIELDS = ("name", "trigger_type", "action_type")


def export_workflow_to_yaml(workflow: Workflow) -> str:
    """Serializa un Workflow a YAML estable (ordered keys, sin tags Python)."""
    payload = {
        "name": workflow.name,
        "description": workflow.description,
        "trigger_type": workflow.trigger_type,
        "trigger_config": dict(workflow.trigger_config or {}),
        "action_type": workflow.action_type,
        "action_config": dict(workflow.action_config or {}),
        "execution_mode": workflow.execution_mode or "reasoning",
        "compiled_steps": list(workflow.compiled_steps) if workflow.compiled_steps else None,
    }
    return yaml.safe_dump(payload, sort_keys=True, allow_unicode=True, default_flow_style=False)


def _parse_yaml(yaml_str: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        raise WorkflowYamlError(f"YAML inválido: {e}") from e
    if not isinstance(data, dict):
        raise WorkflowYamlError("El YAML raíz debe ser un mapping (clave/valor).")

    extra = set(data.keys()) - set(_EXPORTED_FIELDS) - {"tags"}
    if extra:
        raise WorkflowYamlError(f"Campos no soportados en el YAML: {sorted(extra)}")

    for required in _REQUIRED_FIELDS:
        if not data.get(required):
            raise WorkflowYamlError(f"Falta campo obligatorio: {required}")

    if not isinstance(data.get("trigger_config", {}), dict):
        raise WorkflowYamlError("trigger_config debe ser un mapping (dict).")
    if not isinstance(data.get("action_config", {}), dict):
        raise WorkflowYamlError("action_config debe ser un mapping (dict).")
    return data


async def import_yaml_as_workflow(
    db: AsyncSession,
    tenant_id: UUID,
    yaml_str: str,
    *,
    created_by: UUID | None = None,
) -> dict[str, Any]:
    """Crea un Workflow del tenant desde YAML. Siempre inactivo al inicio."""
    data = _parse_yaml(yaml_str)
    wf = Workflow(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        created_by=created_by,
        name=str(data["name"]),
        description=data.get("description"),
        is_active=False,
        trigger_type=str(data["trigger_type"]),
        trigger_config=dict(data.get("trigger_config") or {}),
        action_type=str(data["action_type"]),
        action_config=dict(data.get("action_config") or {}),
        execution_mode=str(data.get("execution_mode") or "reasoning"),
        compiled_steps=list(data["compiled_steps"]) if data.get("compiled_steps") else None,
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return {
        "workflow_id": str(wf.id),
        "name": wf.name,
        "is_active": False,
    }
