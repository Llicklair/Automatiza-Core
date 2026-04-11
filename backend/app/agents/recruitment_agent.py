"""
Agente de Reclutamiento — Parsing de CVs, scoring y gestión de candidatos.

Lee PDFs de currículum, extrae datos estructurados, puntúa contra puestos
abiertos y gestiona el pipeline de selección.
"""

import json
import logging
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.base import AgentState
from app.core.llm_factory import get_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Agente de Reclutamiento de una PYME española.
Tu misión es ayudar en la gestión de procesos de selección:

- Crear y gestionar puestos abiertos (recruitment_positions)
- Procesar CVs recibidos: parsear PDF, extraer datos, puntuar
- Listar candidatos, filtrar por habilidades o puntuación
- Mover candidatos en el pipeline (new → reviewed → shortlisted → rejected → hired)

Siempre opera dentro del tenant del usuario. Sé conciso y profesional.
Cuando proceses un CV, muestra los datos extraídos y la puntuación.
"""


@tool
async def create_position(
    tenant_id: str,
    title: str,
    department: str = "",
    description: str = "",
    required_skills: str = "[]",
    experience_min_years: float = 0,
    salary_range_min: float = 0,
    salary_range_max: float = 0,
) -> str:
    """Crea un nuevo puesto abierto para reclutar.
    required_skills es un JSON array de strings, ej: '["Python", "SQL"]'
    """
    from app.db.base import AsyncSessionLocal
    from app.db.models.hr import RecruitmentPosition

    try:
        skills = (
            json.loads(required_skills) if isinstance(required_skills, str) else required_skills
        )
    except json.JSONDecodeError:
        skills = [s.strip() for s in required_skills.split(",") if s.strip()]

    async with AsyncSessionLocal() as db:
        pos = RecruitmentPosition(
            tenant_id=UUID(tenant_id),
            title=title,
            department=department,
            description=description,
            required_skills=skills,
            experience_min_years=experience_min_years,
            salary_range_min=salary_range_min if salary_range_min else None,
            salary_range_max=salary_range_max if salary_range_max else None,
        )
        db.add(pos)
        await db.commit()
        await db.refresh(pos)
        return json.dumps(
            {
                "id": str(pos.id),
                "title": pos.title,
                "department": pos.department,
                "required_skills": pos.required_skills,
                "status": pos.status,
            },
            ensure_ascii=False,
        )


@tool
async def list_positions(tenant_id: str, status: str = "open") -> str:
    """Lista los puestos abiertos del tenant. status: open|closed|paused|all"""
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.hr import RecruitmentPosition

    async with AsyncSessionLocal() as db:
        q = select(RecruitmentPosition).where(RecruitmentPosition.tenant_id == UUID(tenant_id))
        if status != "all":
            q = q.where(RecruitmentPosition.status == status)
        result = await db.execute(q.order_by(RecruitmentPosition.created_at.desc()))
        positions = result.scalars().all()

    if not positions:
        return "No hay puestos abiertos."

    lines = []
    for p in positions:
        skills = ", ".join(p.required_skills or [])
        lines.append(
            f"- {p.title} ({p.department or 'Sin dept.'}) | Skills: {skills} | Estado: {p.status} | ID: {p.id}"
        )
    return "\n".join(lines)


@tool
async def process_cv(tenant_id: str, position_id: str, cv_file_path: str) -> str:
    """Procesa un CV (PDF): extrae datos, puntúa contra el puesto y guarda el candidato.
    cv_file_path: ruta al archivo PDF del CV.
    position_id: UUID del puesto al que aplica.
    """
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.hr import Candidate, RecruitmentPosition
    from app.services.cv_parser import extract_cv_data, parse_cv_file, score_candidate

    # 1. Parsear PDF
    cv_text = await parse_cv_file(cv_file_path)
    if not cv_text:
        return "Error: no se pudo extraer texto del PDF."

    # 2. Extraer datos estructurados
    cv_data = await extract_cv_data(cv_text)

    # 3. Obtener puesto y puntuar
    async with AsyncSessionLocal() as db:
        pos_result = await db.execute(
            select(RecruitmentPosition).where(
                RecruitmentPosition.id == UUID(position_id),
                RecruitmentPosition.tenant_id == UUID(tenant_id),
            )
        )
        position = pos_result.scalars().first()
        if not position:
            return f"Error: puesto {position_id} no encontrado."

        pos_data = {
            "title": position.title,
            "department": position.department,
            "required_skills": position.required_skills or [],
            "experience_min_years": float(position.experience_min_years or 0),
        }

    scoring = await score_candidate(cv_data, pos_data)

    # 4. Guardar candidato
    async with AsyncSessionLocal() as db:
        candidate = Candidate(
            tenant_id=UUID(tenant_id),
            position_id=UUID(position_id),
            name=cv_data.get("name") or "Nombre no detectado",
            email=cv_data.get("email"),
            phone=cv_data.get("phone"),
            skills=cv_data.get("skills", []),
            experience_years=cv_data.get("experience_years"),
            languages=cv_data.get("languages", []),
            education=cv_data.get("education"),
            summary=cv_data.get("summary"),
            raw_cv_text=cv_text[:10000],
            cv_file_path=cv_file_path,
            score=scoring.get("score", 0),
            score_breakdown=scoring.get("breakdown"),
            status="new",
        )
        db.add(candidate)
        await db.commit()
        await db.refresh(candidate)

    return json.dumps(
        {
            "candidate_id": str(candidate.id),
            "name": candidate.name,
            "email": candidate.email,
            "skills": candidate.skills,
            "experience_years": float(candidate.experience_years)
            if candidate.experience_years
            else None,
            "score": float(candidate.score) if candidate.score else 0,
            "score_breakdown": scoring.get("breakdown", {}),
            "strengths": scoring.get("strengths", []),
            "gaps": scoring.get("gaps", []),
        },
        ensure_ascii=False,
    )


@tool
async def list_candidates(
    tenant_id: str,
    position_id: str = "",
    status: str = "all",
    min_score: float = 0,
) -> str:
    """Lista candidatos. Filtra por puesto, estado o puntuación mínima."""
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.hr import Candidate

    async with AsyncSessionLocal() as db:
        q = select(Candidate).where(Candidate.tenant_id == UUID(tenant_id))
        if position_id:
            q = q.where(Candidate.position_id == UUID(position_id))
        if status != "all":
            q = q.where(Candidate.status == status)
        if min_score > 0:
            q = q.where(Candidate.score >= min_score)
        result = await db.execute(q.order_by(Candidate.score.desc().nullslast()))
        candidates = result.scalars().all()

    if not candidates:
        return "No hay candidatos que coincidan con los filtros."

    lines = []
    for c in candidates:
        score = f"{float(c.score):.0f}" if c.score else "—"
        skills = ", ".join((c.skills or [])[:5])
        lines.append(
            f"- {c.name} | Score: {score} | Skills: {skills} | Estado: {c.status} | ID: {c.id}"
        )
    return "\n".join(lines)


@tool
async def update_candidate_status(tenant_id: str, candidate_id: str, new_status: str) -> str:
    """Mueve un candidato en el pipeline. new_status: new|reviewed|shortlisted|rejected|hired"""
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.hr import Candidate

    valid = {"new", "reviewed", "shortlisted", "rejected", "hired"}
    if new_status not in valid:
        return f"Estado inválido. Opciones: {', '.join(valid)}"

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Candidate).where(
                Candidate.id == UUID(candidate_id),
                Candidate.tenant_id == UUID(tenant_id),
            )
        )
        c = result.scalars().first()
        if not c:
            return f"Candidato {candidate_id} no encontrado."
        old = c.status
        c.status = new_status
        await db.commit()
        return f"Candidato {c.name}: {old} → {new_status}"


# ── Grafo LangGraph ──────────────────────────────────────────────────────────

_tools = [create_position, list_positions, process_cv, list_candidates, update_candidate_status]


async def _agent_node(state: AgentState) -> dict:
    llm = get_llm(temperature=0).bind_tools(_tools)
    if not state.get("messages"):
        state["messages"] = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=state.get("user_intent", "Lista los puestos abiertos")),
        ]
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


def _finalize(state: AgentState) -> dict:
    last = state["messages"][-1] if state.get("messages") else None
    content = last.content if last and isinstance(last.content, str) else "Operación completada."
    return {
        "status": "done",
        "agent_results": [{"agent": "recruitment", "result": content, "status": "completed"}],
    }


_graph = StateGraph(AgentState)
_graph.add_node("agent", _agent_node)
_graph.add_node("tools", ToolNode(_tools))
_graph.add_node("finalize", _finalize)
_graph.set_entry_point("agent")
_graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", "__end__": "finalize"})
_graph.add_edge("tools", "agent")
_graph.add_edge("finalize", END)

graph = _graph.compile()
