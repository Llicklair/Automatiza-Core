"""Skills modulares del orquestador (OOP, BaseSkill.run()).

NO confundir con app.agents.tool_registry, que registra @tool de LangChain
para invocación directa en workflows. Ambos sistemas son complementarios:
  - tool_registry → call_tool("create_invoice", {...})  (determinista)
  - SkillRegistry → skill.run(input_data, tenant_id)    (orquestador)
"""
from .base import BaseSkill, SkillInput
from .registry import SkillRegistry

__all__ = ["BaseSkill", "SkillInput", "SkillRegistry"]
