"""
Workflow agent — tools: compilación de pasos deterministas.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.prompts import load_prompt

logger = logging.getLogger(__name__)

_COMPILE_STEPS_PROMPT = load_prompt("workflow_compile_steps")


async def compile_deterministic_steps(
    name: str,
    description: str,
    trigger_type: str,
    action_instruction: str,
) -> list[dict[str, Any]]:
    """
    Segunda llamada al LLM para compilar los pasos concretos de ejecución
    determinista del workflow. Se llama una sola vez al crear la regla.
    """
    from app.core.llm_factory import get_llm

    llm = get_llm(temperature=0, format_output="json")

    context = (
        f"Workflow: {name}\n"
        f"Descripción: {description}\n"
        f"Tipo de trigger: {trigger_type}\n"
        f"Instrucción de acción: {action_instruction}"
    )

    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=_COMPILE_STEPS_PROMPT),
                HumanMessage(content=context),
            ]
        )
        raw = response.content.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]
        parsed = json.loads(raw.strip())
        steps = parsed.get("steps", [])
        if not isinstance(steps, list):
            steps = []
        for step in steps:
            if "type" not in step:
                step["type"] = "deterministic" if step.get("tool") else "reasoning"
        return steps
    except Exception as e:
        logger.warning("Error parseando pasos de workflow del LLM, usando fallback genérico: %s", e)
        return [
            {
                "type": "reasoning",
                "agent": "skill",
                "action": "execute_workflow",
                "params": {"intent": action_instruction},
            }
        ]
