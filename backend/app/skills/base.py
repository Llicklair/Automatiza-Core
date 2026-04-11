from abc import ABC, abstractmethod
from typing import Any, Dict

from pydantic import BaseModel


class SkillInput(BaseModel):
    """Esquema base para la entrada de parámetros de cualquier Skill."""

    pass


class BaseSkill(ABC):
    """
    Clase base de la que heredan todas las Skills del sistema.
    Una Skill es una herramienta encapsulada que realiza una acción muy específica.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre identificativo único de la Skill. Ej: check_weather"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción clara para que el LLM (el agente) entienda para qué sirve y cuándo usarla."""
        pass

    @property
    @abstractmethod
    def input_schema(self):
        """El modelo Pydantic que define los parámetros de entrada."""
        pass

    @abstractmethod
    async def run(self, input_data: Dict[str, Any], tenant_id: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta la acción de la Skill.

        Args:
            input_data: Parámetros del input serializados.
            tenant_id: ID del Tenant en contexto.
            **kwargs: Puede incluir `db_session`, `user_id`, etc.

        Returns:
            Dict con los resultados u observaciones de la ejecución.
        """
        pass
