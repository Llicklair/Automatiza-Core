import logging
from typing import Any, Dict

from pydantic import Field

from app.skills.base import BaseSkill, SkillInput

logger = logging.getLogger(__name__)

class HelloWorldInput(SkillInput):
    name: str = Field(description="Nombre de la persona a saludar.")
    uppercase: bool = Field(default=False, description="Si es True, el saludo será en mayúsculas.")

class HelloWorldSkill(BaseSkill):
    """
    Skill de demostración que simplemente devuelve un saludo personalizado.
    Útil para probar que el Orquestador y el Registry funcionan conectando nodos de Skills.
    """

    @property
    def name(self) -> str:
        return "hello_world"

    @property
    def description(self) -> str:
        return "Saluda al usuario por su nombre. Útil para verificar que el sistema de Skills funciona."

    @property
    def input_schema(self):
        return HelloWorldInput

    async def run(self, input_data: Dict[str, Any], tenant_id: str, **kwargs) -> Dict[str, Any]:
        """Ejecuta el saludo."""
        name = input_data.get("name", "Desconocido")
        uppercase = input_data.get("uppercase", False)

        greeting = f"Hola, {name}! Bienvenido al sistema de automatizaciones modulares."

        if uppercase:
            greeting = greeting.upper()

        logger.info(f"[Skill Execution] HelloWorldSkill: {greeting}")

        return {
            "success": True,
            "message": greeting,
            "metadata": {
                "tenant_id": tenant_id,
                "is_upper": uppercase
            }
        }
