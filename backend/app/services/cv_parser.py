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

_EXTRACTION_PROMPT = """\
Eres un extractor de información de currículums vitae (CV).
Analiza el texto del CV y devuelve un JSON con esta estructura exacta:

{
  "name": "Nombre completo",
  "email": "email@ejemplo.com",
  "phone": "+34 600 000 000",
  "skills": ["Python", "SQL", "React"],
  "experience_years": 5.0,
  "languages": [{"lang": "Español", "level": "nativo"}, {"lang": "Inglés", "level": "B2"}],
  "education": "Grado en Ingeniería Informática, Universidad X (2018)",
  "summary": "Resumen profesional de 2-3 frases"
}

REGLAS:
- Devuelve SOLO JSON, sin texto adicional.
- Si un campo no se puede extraer, usa null.
- experience_years: estima el total de años de experiencia laboral.
- skills: tecnologías, herramientas, metodologías mencionadas.
- languages: idiomas con nivel estimado (nativo, C2, C1, B2, B1, A2).
- summary: genera un resumen profesional conciso del candidato.
"""

_SCORING_PROMPT = """\
Eres un evaluador de candidatos para procesos de selección.
Evalúa la compatibilidad entre un candidato y un puesto.

PUESTO:
- Título: {title}
- Departamento: {department}
- Habilidades requeridas: {required_skills}
- Experiencia mínima: {experience_min} años

CANDIDATO:
- Habilidades: {candidate_skills}
- Experiencia: {candidate_exp} años
- Idiomas: {candidate_langs}
- Resumen: {candidate_summary}

Devuelve SOLO un JSON con esta estructura:
{{
  "score": 75,
  "breakdown": {{
    "skills_match": 80,
    "experience_match": 70,
    "languages_match": 90,
    "overall_fit": 75
  }},
  "strengths": ["Domina React y Node.js", "5 años de experiencia"],
  "gaps": ["No tiene experiencia con Docker"]
}}

score es un número 0-100. Sé justo pero exigente.
"""


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
    from app.services.pdf_parser import parse_pdf

    result = await parse_pdf(file_path)
    return result.markdown if result else ""
