import importlib
import inspect
import logging
from pathlib import Path

from app.skills.base import BaseSkill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Registro y cargador dinámico de Skills (Habilidades Modulares)."""

    _skills: dict[str, BaseSkill] = {}

    @classmethod
    def register(cls, skill: BaseSkill):
        """Registra manualmente un Skill instanciado."""
        if skill.name in cls._skills:
            logger.warning(f"Sobrescribiendo Skill ya existente: {skill.name}")
        cls._skills[skill.name] = skill
        logger.info(f"Skill registrada: {skill.name}")

    @classmethod
    def get_skill(cls, name: str) -> BaseSkill | None:
        """Devuelve la instancia de la Skill o None si no existe."""
        return cls._skills.get(name)

    @classmethod
    def get_all_skills(cls) -> list[BaseSkill]:
        """Devuelve todas las Skills registradas."""
        return list(cls._skills.values())

    @classmethod
    def load_builtins(cls):
        """Escanea dinámicamente el directorio actual de skills y las auto-registra."""
        skills_dir = Path(__file__).parent

        for file in skills_dir.glob("*.py"):
            if file.name.startswith("_") or file.name in ["base.py", "registry.py"]:
                continue

            module_name = f"app.skills.{file.stem}"
            try:
                module = importlib.import_module(module_name)
                # Buscar clases concretas que hereden de BaseSkill
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseSkill) and obj is not BaseSkill:
                        # Para evitar instanciar clases abstractas (ABC)
                        if not inspect.isabstract(obj):
                            cls.register(obj())
            except Exception as e:
                logger.error(f"Error cargando módulo de Skill {module_name}: {e}")


# Ejecutar carga al inicializar
SkillRegistry.load_builtins()
