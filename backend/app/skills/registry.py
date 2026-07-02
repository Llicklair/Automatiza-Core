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

        # Descubre por stem, aceptando .py (dev) y .pyc (build sin fuente): en el
        # instalador se compila a bytecode y se borran los .py, así que buscar
        # solo *.py dejaría cero skills. Deduplica por stem si coexisten ambos.
        stems: set[str] = set()
        for file in list(skills_dir.glob("*.py")) + list(skills_dir.glob("*.pyc")):
            stem = file.stem  # "mod" tanto para mod.py como para mod.pyc
            if stem.startswith("_") or stem in ("base", "registry"):
                continue
            stems.add(stem)

        for stem in sorted(stems):
            module_name = f"app.skills.{stem}"
            try:
                module = importlib.import_module(module_name)
                # Buscar clases concretas que hereden de BaseSkill
                for _name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseSkill) and obj is not BaseSkill:
                        # Para evitar instanciar clases abstractas (ABC)
                        if not inspect.isabstract(obj):
                            cls.register(obj())
            except Exception as e:
                logger.error(f"Error cargando módulo de Skill {module_name}: {e}")


# Ejecutar carga al inicializar
SkillRegistry.load_builtins()
