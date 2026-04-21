"""Funciones NLP: parsing de lenguaje natural y disparo de eventos."""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.llm_factory import get_llm
from app.db.models import models
from app.prompts import load_prompt
from app.services.workflow._ui_graph import generate_preview_nodes

logger = logging.getLogger(__name__)


async def parse_natural_language(text: str) -> dict:
    """Convierte prompt de lenguaje natural en configuracion de workflow.

    Raises Exception si el LLM no puede parsear.
    """
    llm = get_llm(temperature=0, format_output="json")
    llm_plain = get_llm(temperature=0)

    sys_prompt = load_prompt("workflow_parse")
    response = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=text)])
    raw = response.content.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.endswith("```"):
        raw = raw[:-3]
    payload = json.loads(raw.strip())

    # Deteccion de determinismo
    can_det = False
    try:
        instruction = payload.get("action_config", {}).get("instruction", text)
        det_prompt = load_prompt("workflow_determinism_check")
        det_response = llm_plain.invoke([
            SystemMessage(content=det_prompt),
            HumanMessage(content=instruction),
        ])
        can_det = det_response.content.strip().lower().startswith("true")
    except Exception as det_err:
        logger.warning("Fallo deteccion determinismo: %s", det_err)
    payload["can_be_deterministic"] = can_det

    preview_nodes, preview_edges = generate_preview_nodes(payload)
    payload["ui_nodes"] = preview_nodes
    payload["ui_edges"] = preview_edges
    return payload


async def fire_event(
    event_name: str, context: dict, tenant_id, user_id, db: AsyncSession,
) -> list[str]:
    """Dispara todos los workflows activos que coincidan con el evento. Retorna IDs disparados."""
    from app.services.workflow._execution import (
        _build_ai_instruction,
        _dispatch_deterministic,
        _dispatch_reasoning,
    )

    result = await db.execute(
        select(models.Workflow).where(
            models.Workflow.tenant_id == tenant_id,
            models.Workflow.is_active.is_(True),
            models.Workflow.trigger_type == "event_based",
        )
    )
    workflows = result.scalars().all()

    triggered = []
    for wf in workflows:
        wf_events = wf.trigger_config.get("events", [])
        if event_name not in wf_events and "any" not in wf_events:
            continue

        execution = models.WorkflowExecution(
            workflow_id=wf.id,
            tenant_id=tenant_id,
            status="running",
            trigger_payload={"event": event_name, "context": context},
        )
        db.add(execution)
        await db.flush()

        extra_meta = {"event": event_name}
        if wf.execution_mode == "deterministic" and wf.compiled_steps:
            await _dispatch_deterministic(
                db, wf, execution, tenant_id, user_id,
                f"[Determinista] ({event_name})", extra_meta,
            )
            if execution.status == "success":
                triggered.append(str(wf.id))
            await db.commit()
        else:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            intent = f"{_build_ai_instruction(wf)} [Contexto: {event_name} - {context_str}]"
            await _dispatch_reasoning(db, wf, execution, tenant_id, user_id, intent, extra_meta)
            if execution.status != "failed":
                triggered.append(str(wf.id))
            await db.commit()

    return triggered
