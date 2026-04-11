from typing import Any, List

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.db.models import models
from app.middleware.rate_limit import limiter
from app.skills.registry import SkillRegistry

router = APIRouter(prefix="/skills", tags=["Skills & Integrations"])


class SkillResponse(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


@router.get("/", response_model=List[SkillResponse])
@limiter.limit("30/minute")
async def list_available_skills(
    request: Request, current_user: models.User = Depends(get_current_user)
):
    """
    Devuelve la lista de Skills (Habilidades/Nodos) disponibles en el sistema
    para que el frontend pueda mostrarlas en la paleta del grafo o en la UI.
    """
    skills = SkillRegistry.get_all_skills()

    response = []
    for skill in skills:
        # Extraemos el JSON schema de Pydantic
        schema = skill.input_schema.model_json_schema()
        response.append(
            {"name": skill.name, "description": skill.description, "input_schema": schema}
        )

    return response
