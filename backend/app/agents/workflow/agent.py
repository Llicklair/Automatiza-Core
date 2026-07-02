"""
Workflow agent â€” orquestación principal: LLM â†’ parse â†’ DB â†’ resultado.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import Workflow
from app.prompts import load_prompt

from .tools import compile_deterministic_steps

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = load_prompt("workflow_agent")


@dataclass
class WorkflowAgentResult:
    success: bool
    action: str  # create | update | delete | list | toggle
    workflow_id: str | None = None
    workflow_name: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    compiled_steps: list[dict[str, Any]] | None = None


async def run_workflow_agent(
    user_intent: str,
    tenant_id: str,
    user_id: str | None = None,
    task_id: str | None = None,
    execution_mode: str = "reasoning",
) -> WorkflowAgentResult:
    """
    Orquestación del agente de workflows: LLM -> Interpretación -> DB -> Resultado.

    Args:
        execution_mode: 'reasoning' (por defecto) o 'deterministic'.
            En modo 'deterministic', tras el parse inicial se compilan los pasos
            concretos del workflow y se almacenan en compiled_steps.
    """
    try:
        from app.core.llm_factory import get_llm

        llm = get_llm(temperature=0, format_output="json")

        current_context = ""
        if any(w in user_intent.lower() for w in ["modifica", "actualiza", "cambia", "borra", "quita", "desactiva"]):
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Workflow).where(Workflow.tenant_id == uuid.UUID(tenant_id)))
                wfs = result.scalars().all()
                if wfs:
                    current_context = "\nWorkflows actuales del tenant:\n" + "\n".join(
                        f"- ID: {w.id}, Nombre: {w.name}, Trigger: {w.trigger_type}, Activo: {w.is_active}" for w in wfs
                    )

        response = await llm.ainvoke(
            [
                SystemMessage(content=_SYSTEM_PROMPT + current_context),
                HumanMessage(content=user_intent),
            ]
        )

        try:
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.rsplit("```", 1)[0].strip()
            plan = json.loads(raw)
        except Exception as e:
            logger.warning("Error parseando respuesta JSON del LLM en workflow_agent: %s", e)
            return WorkflowAgentResult(success=False, action="parse", error="No se pudo parsear el plan del LLM.")

        action = plan.get("action", "create")

        async with AsyncSessionLocal() as db:
            if action == "create":
                wf_name = plan.get("name", "Nueva Automática")
                wf_description = plan.get("description", "")
                wf_trigger_type = plan.get("trigger_type", "event_based")
                wf_action_config = plan.get("action_config", {})
                wf_action_instruction = wf_action_config.get("instruction", wf_description or wf_name)

                compiled_steps = None
                if execution_mode == "deterministic":
                    compiled_steps = await compile_deterministic_steps(
                        name=wf_name,
                        description=wf_description,
                        trigger_type=wf_trigger_type,
                        action_instruction=wf_action_instruction,
                    )

                new_wf = Workflow(
                    tenant_id=uuid.UUID(tenant_id),
                    created_by=uuid.UUID(user_id) if user_id else None,
                    name=wf_name,
                    description=wf_description,
                    trigger_type=wf_trigger_type,
                    trigger_config=plan.get("trigger_config", {}),
                    action_type=plan.get("action_type", "create_task"),
                    action_config=wf_action_config,
                    ui_nodes=plan.get("ui_nodes", []),
                    ui_edges=plan.get("ui_edges", []),
                    is_active=plan.get("is_active", True),
                    execution_mode=execution_mode,
                    compiled_steps=compiled_steps,
                )
                db.add(new_wf)
                await db.commit()
                await db.refresh(new_wf)
                return WorkflowAgentResult(
                    success=True,
                    action="create",
                    workflow_id=str(new_wf.id),
                    workflow_name=new_wf.name,
                    data=plan,
                    compiled_steps=compiled_steps,
                )

            elif action in ["update", "toggle", "delete"]:
                wf_id = plan.get("workflow_id")
                if not wf_id:
                    res = await db.execute(
                        select(Workflow)
                        .where(
                            Workflow.tenant_id == uuid.UUID(tenant_id),
                            Workflow.name.ilike(f"%{plan.get('name')}%"),
                        )
                        .limit(1)
                    )
                    existing_wf = res.scalar_one_or_none()
                else:
                    existing_wf = await db.get(Workflow, uuid.UUID(wf_id))

                if not existing_wf or str(existing_wf.tenant_id) != tenant_id:
                    return WorkflowAgentResult(
                        success=False, action=action, error="No se encontró el workflow indicado."
                    )

                if action == "delete":
                    await db.delete(existing_wf)
                    await db.commit()
                    return WorkflowAgentResult(success=True, action="delete", workflow_id=str(existing_wf.id))

                if "is_active" in plan:
                    existing_wf.is_active = plan["is_active"]
                if "trigger_config" in plan:
                    existing_wf.trigger_config = plan["trigger_config"]
                if "action_config" in plan:
                    existing_wf.action_config = plan["action_config"]

                await db.commit()
                return WorkflowAgentResult(
                    success=True,
                    action=action,
                    workflow_id=str(existing_wf.id),
                    workflow_name=existing_wf.name,
                    data=plan,
                )

            elif action == "list":
                res = await db.execute(select(Workflow).where(Workflow.tenant_id == uuid.UUID(tenant_id)))
                wfs = res.scalars().all()
                data_list = [{"id": str(w.id), "name": w.name, "active": w.is_active} for w in wfs]
                return WorkflowAgentResult(success=True, action="list", data={"workflows": data_list})

        return WorkflowAgentResult(success=False, action=action, error="Accion no soportada o error en DB.")

    except Exception as e:
        import traceback

        return WorkflowAgentResult(success=False, action="error", error=str(e), data={"trace": traceback.format_exc()})
