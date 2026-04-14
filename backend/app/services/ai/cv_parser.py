"""
Servicio de parsing de CVs.

Extrae texto de PDFs con pdf_parser existente y luego usa LLM
para normalizar la información en campos estructurados.
"""

import json
import logging
from typing import Any

from app.core.llm_factory import get_llm

logger = logging.getLogger(__name__)

from app.prompts import load_prompt

_EXTRACTION_PROMPT = load_prompt("cv_extraction")

_SCORING_PROMPT = load_prompt("cv_scoring")


async def extract_cv_data(cv_text: str) -> dict[str, Any]:
    """Extrae datos estructurados de un CV usando LLM."""
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = get_llm(temperature=0)
    response = await llm.ainvoke(
        [
            SystemMessage(content=_EXTRACTION_PROMPT),
            HumanMessage(content=f"CV:\n\n{cv_text[:8000]}"),
        ]
    )

    raw = response.content.strip()
    # Limpiar markdown fences si las hay
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM devolvió JSON inválido para CV, intentando extracción parcial")
        return {
            "name": None,
            "email": None,
            "phone": None,
            "skills": [],
            "experience_years": None,
            "languages": [],
            "education": None,
            "summary": raw[:500],
        }


async def score_candidate(candidate_data: dict, position_data: dict) -> dict[str, Any]:
    """Puntúa un candidato contra un puesto usando LLM."""
    from langchain_core.messages import HumanMessage, SystemMessage

    prompt = _SCORING_PROMPT.format(
        title=position_data.get("title", ""),
        department=position_data.get("department", ""),
        required_skills=", ".join(position_data.get("required_skills", [])),
        experience_min=position_data.get("experience_min_years", 0),
        candidate_skills=", ".join(candidate_data.get("skills", [])),
        candidate_exp=candidate_data.get("experience_years", "desconocido"),
        candidate_langs=json.dumps(candidate_data.get("languages", []), ensure_ascii=False),
        candidate_summary=candidate_data.get("summary", "Sin resumen"),
    )

    llm = get_llm(temperature=0)
    response = await llm.ainvoke(
        [
            SystemMessage(content="Eres un evaluador de RRHH experto. Responde SOLO con JSON."),
            HumanMessage(content=prompt),
        ]
    )

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM devolvió JSON inválido para scoring")
        return {"score": 0, "breakdown": {}, "strengths": [], "gaps": ["Error en evaluación"]}


async def parse_cv_file(file_path: str) -> str:
    """Lee un PDF y extrae el texto usando el parser existente."""
    from app.services.pdf.parser import parse_pdf

    result = await parse_pdf(file_path)
    return result.markdown if result else ""
